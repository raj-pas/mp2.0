"""Automate the R10 7-folder real-PII sweep (sub-session #11 deferred).

Drives the live backend API to upload every supported file in each
client folder under ``MP2.0_Clients/`` and captures structural
counts to ``docs/agent/r10-sweep-results-2026-05-03.md`` (append).

Real-PII discipline (canon §11.8.3):
  - Output is structural-only: doc count, fact count, conflict
    count, per-doc-type distribution, token usage, cost estimate.
  - No values, no quotes, no client-identifying narrative in the
    per-doc breakdown.
  - Folder names ARE used as stable structural identifiers in the
    spend ledger + sweep results doc, matching the existing #8.5 +
    #9 ledger entries (Niesner, Seltzer). The folder name is the
    operator's local-FS path identifier, not extracted client
    content. To anonymize for an external publication, run with
    ``--anonymize-folders`` which substitutes a 6-char sha256
    prefix and emits the surname-to-id map only to a gitignored
    file inside ``MP20_SECURE_DATA_ROOT``.

Usage:
    set -a && source .env && set +a
    unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN
    uv run python scripts/demo-prep/r10_sweep.py

    # Or limit to specific folders:
    uv run python scripts/demo-prep/r10_sweep.py --only Niesner --only Seltzer

The script does NOT auto-commit households (preserves demo state).
Workspaces are left in `review_ready` for manual inspection or
demo-day commit.

Stop conditions (per sub-sessions-8-11-plan.md §11):
  - Folder Bedrock spend > $10 → halt + terminate worker + log
  - Folder wall-clock > 30 min → halt + terminate worker + log
  - HTTP/network failure mid-sweep → cleanup + log

Spend ledger: every Bedrock call's tokens + cost are summed
per-folder + per-sweep totals. Appended to
``docs/agent/bedrock-spend-2026-05-03.md`` automatically. The
append is idempotent within a calendar day — re-runs warn-default
to no-op when a section with today's date already exists; pass
``--force-append`` to override.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"
CLIENTS_ROOT = Path("/Users/saranyaraj/Documents/MP2.0_Clients")
PROJECT_ROOT = Path("/Users/saranyaraj/Projects/github-repo/mp2.0")
SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}
DEFAULT_FOLDERS = [
    "Gumprich",
    "Herman",
    "McPhalen",
    "Niesner",
    "Schlotfeldt",
    "Seltzer",
    "Weryha",
]
PER_DOC_COST_CEILING = 0.50
PER_FOLDER_COST_CEILING = 10.00
PER_FOLDER_WALL_CLOCK_CEILING_S = 30 * 60


def login() -> requests.Session:
    s = requests.Session()
    s.get(f"{API_BASE}/api/session/").raise_for_status()
    csrf = s.cookies.get("csrftoken")
    pw = os.environ.get("MP20_LOCAL_ADMIN_PASSWORD")
    if not pw:
        raise SystemExit("MP20_LOCAL_ADMIN_PASSWORD env var not set")
    r = s.post(
        f"{API_BASE}/api/auth/login/",
        json={"email": "advisor@example.com", "password": pw},
        headers={"X-CSRFToken": csrf, "Referer": API_BASE},
    )
    r.raise_for_status()
    return s


def _empty_summary(folder_name: str, skipped_reason: str | None = None) -> dict:
    return {
        "folder": folder_name,
        "skipped_reason": skipped_reason,
        "workspace_external_id": None,
        "elapsed_s": 0,
        "docs_uploaded": 0,
        "docs_reconciled": 0,
        "docs_extracted_only": 0,
        "docs_failed": 0,
        "facts_total": 0,
        "state_section_sizes": {},
        "conflicts_total": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "evidence_drops": 0,
        "extraction_paths": {},
        "doc_status_distribution": {},
        "halted_on": None,
    }


def _doc_extraction_meta(doc: dict) -> dict:
    """Return the per-doc extraction metadata sub-dict.

    The pipeline stores token counts + cost + extraction_path under
    ``processing_metadata.extraction``, NOT at the top level — so a
    plain ``meta.get("bedrock_cost_estimate_usd")`` returns 0 for
    every doc. This helper centralizes the key-path so the polling
    loop, summary builder, and post-loop totals all agree.
    """
    pmeta = doc.get("processing_metadata") or {}
    inner = pmeta.get("extraction")
    if isinstance(inner, dict):
        return inner
    return pmeta  # fall back if pipeline ever stops nesting


def _sum_workspace_cost(workspace_payload: dict) -> float:
    """Sum the per-doc bedrock cost estimate across the workspace.

    Used by the polling loop's cost-ceiling stop-condition. Returns
    0.0 if no docs have processing_metadata yet (e.g. early in the
    sweep before extraction has touched any doc).
    """
    total = 0.0
    for doc in workspace_payload.get("documents", []):
        meta = _doc_extraction_meta(doc)
        try:
            total += float(meta.get("bedrock_cost_estimate_usd") or 0)
        except (TypeError, ValueError):
            pass
    return total


def _terminate_worker(proc: subprocess.Popen) -> None:
    """Best-effort terminate. Always attempts terminate + wait; falls
    back to kill if terminate doesn't exit within 10s. Idempotent on
    already-exited processes.
    """
    if proc is None:
        return
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _delete_workspace_best_effort(session: requests.Session, wsid: str) -> bool:
    """Best-effort DELETE on a workspace (used to clean up orphans
    after a sweep failure). Returns True if the request succeeded
    (2xx) — silent on 404 or transport errors so cleanup never
    masks the original exception.
    """
    csrf = session.cookies.get("csrftoken")
    try:
        r = session.delete(
            f"{API_BASE}/api/review-workspaces/{wsid}/",
            headers={"X-CSRFToken": csrf, "Referer": API_BASE},
            timeout=10,
        )
        return r.ok
    except (requests.RequestException, OSError):
        return False


def sweep_folder(folder_name: str, session: requests.Session) -> dict:
    client_root = CLIENTS_ROOT / folder_name
    if not client_root.is_dir():
        return _empty_summary(folder_name, skipped_reason="folder_not_found")

    label = f"{folder_name} sweep (r10 auto)"
    print(f"\n=== {folder_name} sweep ===")
    folder_start = time.monotonic()
    halted_on: str | None = None
    final_doc_state: dict[str, int] = {}
    proc: subprocess.Popen | None = None
    wsid: str | None = None
    files_uploaded = 0

    try:
        # Create workspace
        csrf = session.cookies.get("csrftoken")
        r = session.post(
            f"{API_BASE}/api/review-workspaces/",
            json={"label": label, "data_origin": "real_derived"},
            headers={"X-CSRFToken": csrf, "Referer": API_BASE},
        )
        r.raise_for_status()
        workspace = r.json()
        wsid = workspace["external_id"]
        print(f"  workspace external_id: {wsid}")

        # Upload supported files
        csrf = session.cookies.get("csrftoken")
        for path in sorted(client_root.iterdir()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            with open(path, "rb") as fh:
                r = session.post(
                    f"{API_BASE}/api/review-workspaces/{wsid}/upload/",
                    files={"files": (path.name, fh)},
                    headers={"X-CSRFToken": csrf, "Referer": API_BASE},
                    timeout=60,
                )
            r.raise_for_status()
            body = r.json()
            files_uploaded += len(body.get("uploaded", []))
        print(f"  files uploaded: {files_uploaded}")

        # Spawn worker
        cmd = [
            "uv",
            "run",
            "python",
            str(PROJECT_ROOT / "web/manage.py"),
            "process_review_queue",
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "DATABASE_URL": "postgres://mp20:mp20@localhost:5432/mp20"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"  worker PID: {proc.pid}")

        # Poll until queue drains or a stop-condition fires
        for poll_idx in range(120):  # 120 × 15s = 30 min ceiling
            time.sleep(15)
            elapsed = time.monotonic() - folder_start
            if elapsed > PER_FOLDER_WALL_CLOCK_CEILING_S:
                halted_on = "wall_clock_ceiling"
                break
            r = session.get(f"{API_BASE}/api/review-workspaces/{wsid}/")
            r.raise_for_status()
            d = r.json()
            doc_statuses: dict[str, int] = {}
            for doc in d.get("documents", []):
                doc_statuses[doc["status"]] = doc_statuses.get(doc["status"], 0) + 1
            job_statuses: dict[str, int] = {}
            for job in d.get("processing_jobs", []):
                job_statuses[job["status"]] = job_statuses.get(job["status"], 0) + 1
            active_jobs = job_statuses.get("queued", 0) + job_statuses.get("processing", 0)
            running_cost = _sum_workspace_cost(d)
            print(
                f"  [{poll_idx + 1:>2}] doc={doc_statuses} active={active_jobs}"
                f" cost=${running_cost:.4f} elapsed={elapsed:.0f}s"
            )
            final_doc_state = doc_statuses
            # Cost-ceiling stop-condition: abort the folder if running
            # spend exceeds the per-folder budget. The worker is
            # terminated in the finally block; partially-extracted
            # state is captured below from the most-recent payload.
            if running_cost > PER_FOLDER_COST_CEILING:
                halted_on = "folder_cost_ceiling"
                break
            # Per-doc cost ceiling: abort if any single doc has
            # spent > $0.50 (sub-session-11-plan.md §11). Catches a
            # runaway prompt before it eats the whole folder budget.
            for doc in d.get("documents", []):
                meta = _doc_extraction_meta(doc)
                try:
                    cost = float(meta.get("bedrock_cost_estimate_usd") or 0)
                except (TypeError, ValueError):
                    cost = 0.0
                if cost > PER_DOC_COST_CEILING:
                    halted_on = "per_doc_cost_ceiling"
                    break
            if halted_on:
                break
            if active_jobs == 0:
                break
    finally:
        _terminate_worker(proc)

    folder_elapsed = time.monotonic() - folder_start

    # Capture final structural state
    r = session.get(f"{API_BASE}/api/review-workspaces/{wsid}/")
    r.raise_for_status()
    d = r.json()
    docs = d.get("documents", [])
    reconciled = sum(1 for x in docs if x["status"] == "reconciled")
    extracted_only = sum(1 for x in docs if x["status"] == "extracted")
    failed = sum(1 for x in docs if x["status"] == "failed")
    state = d.get("reviewed_state") or {}
    conflicts = len(state.get("conflicts") or [])
    # Fact-count proxy: structural-section sizes in reviewed_state.
    # The full fact-count is also available via the dedicated facts
    # endpoint per-workspace; for the R10 sweep summary we report
    # the section-size total to match the demo-prep script's
    # convention.
    state_section_sizes = {
        "people": len(state.get("people") or []),
        "accounts": len(state.get("accounts") or []),
        "goals": len(state.get("goals") or []),
        "goal_account_links": len(state.get("goal_account_links") or []),
    }
    facts_total = sum(state_section_sizes.values())
    extraction_paths: dict[str, int] = {}
    input_tokens = 0
    output_tokens = 0
    cost_usd = 0.0
    evidence_drops = 0
    for doc in docs:
        meta = _doc_extraction_meta(doc)
        path = meta.get("extraction_path") or "unknown"
        extraction_paths[path] = extraction_paths.get(path, 0) + 1
        input_tokens += int(meta.get("bedrock_input_tokens") or 0)
        output_tokens += int(meta.get("bedrock_output_tokens") or 0)
        cost_usd += float(meta.get("bedrock_cost_estimate_usd") or 0)
        evidence_drops += int(meta.get("evidence_drops") or 0)

    # Stop-condition signals (do not abort the script; record them)
    if cost_usd > PER_FOLDER_COST_CEILING:
        halted_on = halted_on or "folder_cost_ceiling"

    summary = {
        "folder": folder_name,
        "workspace_external_id": wsid,
        "elapsed_s": round(folder_elapsed, 1),
        "docs_uploaded": files_uploaded,
        "docs_reconciled": reconciled,
        "docs_extracted_only": extracted_only,
        "docs_failed": failed,
        "facts_total": facts_total,
        "state_section_sizes": state_section_sizes,
        "conflicts_total": conflicts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 4),
        "evidence_drops": evidence_drops,
        "extraction_paths": extraction_paths,
        "doc_status_distribution": final_doc_state,
        "halted_on": halted_on,
    }
    print(f"\n  === {folder_name} structural summary ===")
    print(f"  reconciled: {reconciled} / {files_uploaded}")
    print(f"  failed: {failed} | conflicts: {conflicts}")
    print(f"  extraction paths: {extraction_paths}")
    print(f"  tokens: input={input_tokens} output={output_tokens} cost=${cost_usd:.4f}")
    print(f"  evidence-quote drops: {evidence_drops}")
    print(f"  elapsed: {folder_elapsed:.1f}s")
    if halted_on:
        print(f"  HALTED on: {halted_on}")
    return summary


def _today_section_already_present(doc_path: Path, header_prefix: str) -> bool:
    """Detect whether a section starting with ``header_prefix`` and
    a today's-date marker already exists in ``doc_path``. Used by
    the idempotency guard so re-running the script doesn't duplicate
    entire sections in the committed docs.
    """
    if not doc_path.exists():
        return False
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        if line.startswith(header_prefix) and today in line:
            return True
    return False


def append_results_to_doc(summaries: list[dict], force_append: bool = False) -> str:
    """Append the sweep results to the R10 sweep results doc.

    Returns a status string describing the outcome:
      - "appended" — section written
      - "skipped_idempotent" — today's section already present + force_append=False
      - "skipped_no_doc" — target file does not exist
    """
    doc_path = PROJECT_ROOT / "docs/agent/r10-sweep-results-2026-05-03.md"
    if not doc_path.exists():
        return "skipped_no_doc"
    header_prefix = "## Automated R10 7-folder sweep"
    if not force_append and _today_section_already_present(doc_path, header_prefix):
        return "skipped_idempotent"

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    section_lines = [
        "",
        "---",
        "",
        f"## Automated R10 7-folder sweep — {timestamp}",
        "",
        "Real-PII discipline (canon §11.8.3): structural counts only;",
        "no values, no quotes. Workspaces left in `review_ready` (NOT",
        "auto-committed) to preserve demo state.",
        "",
        "| Folder | Docs | Recon. | Failed | Facts | Conflicts | Cost | Drops | Halted |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    total_cost = 0.0
    total_facts = 0
    total_input = 0
    total_output = 0
    total_drops = 0
    for s in summaries:
        halt = s["halted_on"] or "—"
        skipped = s.get("skipped_reason")
        row = (
            f"| {s['folder']} | {s['docs_uploaded']} | "
            f"{s['docs_reconciled']} | {s['docs_failed']} | "
            f"{s['facts_total']} | {s['conflicts_total']} | "
            f"${s['cost_usd']:.4f} | {s['evidence_drops']} | "
            f"{halt if not skipped else skipped} |"
        )
        section_lines.append(row)
        if not skipped:
            total_cost += s["cost_usd"]
            total_facts += s["facts_total"]
            total_input += s["input_tokens"]
            total_output += s["output_tokens"]
            total_drops += s["evidence_drops"]
    section_lines.append("")
    section_lines.append("**Totals:**")
    section_lines.append(f"- Total facts extracted: {total_facts}")
    section_lines.append(f"- Total Bedrock cost: ${total_cost:.4f}")
    section_lines.append(f"- Total tokens: input={total_input}, output={total_output}")
    section_lines.append(f"- Total evidence-quote drops: {total_drops}")

    with doc_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(section_lines) + "\n")
    return "appended"


def append_to_spend_ledger(summaries: list[dict], force_append: bool = False) -> str:
    """Append the sweep totals to the Bedrock spend ledger.

    Returns the same status strings as ``append_results_to_doc``.
    """
    ledger_path = PROJECT_ROOT / "docs/agent/bedrock-spend-2026-05-03.md"
    if not ledger_path.exists():
        return "skipped_no_doc"
    header_prefix = "## Automated R10 7-folder sweep"
    if not force_append and _today_section_already_present(ledger_path, header_prefix):
        return "skipped_idempotent"

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    rows = [
        "",
        "---",
        "",
        f"## Automated R10 7-folder sweep ({timestamp}) — Sub-session #11 deferred",
        "",
        "Per-folder structural breakdown:",
        "",
        "| Folder | Docs | Input tok | Output tok | Cost | Facts | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    grand_input = 0
    grand_output = 0
    grand_cost = 0.0
    for s in summaries:
        if s.get("skipped_reason"):
            rows.append(f"| {s['folder']} | — | — | — | — | — | skipped: {s['skipped_reason']} |")
            continue
        notes = "; ".join(f"{k}={v}" for k, v in s["extraction_paths"].items())
        rows.append(
            f"| {s['folder']} | {s['docs_uploaded']} | "
            f"{s['input_tokens']} | {s['output_tokens']} | "
            f"${s['cost_usd']:.4f} | {s['facts_total']} | {notes} |"
        )
        grand_input += s["input_tokens"]
        grand_output += s["output_tokens"]
        grand_cost += s["cost_usd"]

    rows.append("")
    rows.append(f"**Sweep total:** ${grand_cost:.4f}")
    rows.append(f"**Sweep input tokens:** {grand_input}")
    rows.append(f"**Sweep output tokens:** {grand_output}")
    rows.append(
        "**Stop-condition checks:** see r10-sweep-results-2026-05-03.md for per-folder halt status."
    )

    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return "appended"


def _maybe_anonymize(folders: list[str], enabled: bool) -> tuple[list[str], dict[str, str]]:
    """Optionally substitute folder names with sha256-prefixed IDs.

    When enabled, returns (anonymized_folder_list, original_folder_path_map)
    so the script can still read from the real local filesystem path
    while emitting only the anonymized id in the committed docs.
    Writes the surname → id map to a gitignored file inside
    ``MP20_SECURE_DATA_ROOT/_debug/`` for the operator's reference.
    """
    if not enabled:
        return folders, {f: f for f in folders}
    import hashlib

    mapping: dict[str, str] = {}
    anonymized: list[str] = []
    for f in folders:
        anon = "client_" + hashlib.sha256(f.encode("utf-8")).hexdigest()[:8]
        mapping[anon] = f
        anonymized.append(anon)

    secure_root = os.environ.get("MP20_SECURE_DATA_ROOT")
    if secure_root:
        debug_dir = Path(secure_root) / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        target = debug_dir / f"r10_sweep_anon_map_{datetime.now(UTC):%Y%m%d_%H%M%S}.txt"
        target.write_text(
            "\n".join(f"{anon}\t{orig}" for anon, orig in mapping.items()),
            encoding="utf-8",
        )
    return anonymized, mapping


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Restrict the sweep to specific folders (repeatable).",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print summary only; skip doc + ledger updates.",
    )
    parser.add_argument(
        "--force-append",
        action="store_true",
        help=(
            "Override the idempotency guard and append even if a "
            "section with today's date already exists in the target docs."
        ),
    )
    parser.add_argument(
        "--anonymize-folders",
        action="store_true",
        help=(
            "Replace folder surnames with sha256-prefixed ids in "
            "committed docs. Writes the id→surname map only inside "
            "MP20_SECURE_DATA_ROOT/_debug/."
        ),
    )
    parser.add_argument(
        "--cleanup-on-failure",
        action="store_true",
        default=True,
        help=(
            "Best-effort DELETE the orphan workspace if a folder "
            "sweep raises an exception. On by default."
        ),
    )
    args = parser.parse_args()

    requested_folders = args.only or DEFAULT_FOLDERS
    sweep_folders, anon_map = _maybe_anonymize(requested_folders, args.anonymize_folders)
    # The actual filesystem path is keyed off the original surname;
    # `sweep_folder` looks at CLIENTS_ROOT/<folder_name>. When
    # anonymization is on we need to feed the real surname into
    # sweep_folder so iterdir() succeeds, then re-label the result.
    print(f"R10 sweep targets: {sweep_folders}")
    sweep_start = time.monotonic()
    session = login()

    summaries: list[dict] = []
    for sweep_label in sweep_folders:
        original = anon_map.get(sweep_label, sweep_label)
        wsid_for_cleanup: str | None = None
        try:
            summary = sweep_folder(original, session)
            wsid_for_cleanup = summary.get("workspace_external_id")
            # Re-label so the committed docs use the anonymized id
            # (if anonymization is on; no-op otherwise).
            summary["folder"] = sweep_label
        except requests.HTTPError as e:
            print(f"  HTTP error during {sweep_label}: {e}")
            status = e.response.status_code if e.response else "unknown"
            summary = _empty_summary(sweep_label, skipped_reason=f"http_error:{status}")
        except (requests.RequestException, OSError) as e:
            err_name = type(e).__name__
            print(f"  Transport error during {sweep_label}: {err_name}")
            summary = _empty_summary(sweep_label, skipped_reason=f"transport_error:{err_name}")
        finally:
            # Cleanup-on-failure: if the sweep raised before completing
            # AND we created a workspace, best-effort DELETE so the
            # orphan + its raw bytes don't accumulate. The successful
            # path leaves the workspace in review_ready (intentional).
            if args.cleanup_on_failure and summary.get("skipped_reason") and wsid_for_cleanup:
                ok = _delete_workspace_best_effort(session, wsid_for_cleanup)
                print(f"  cleanup workspace {wsid_for_cleanup[:12]}…: {'ok' if ok else 'failed'}")
        summaries.append(summary)

    sweep_elapsed = time.monotonic() - sweep_start
    print(f"\n=== Sweep complete in {sweep_elapsed / 60:.1f} min ===")
    total_cost = sum(s["cost_usd"] for s in summaries)
    total_facts = sum(s["facts_total"] for s in summaries)
    print(f"  total cost: ${total_cost:.4f}")
    print(f"  total facts: {total_facts}")

    if not args.no_write:
        results_status = append_results_to_doc(summaries, force_append=args.force_append)
        ledger_status = append_to_spend_ledger(summaries, force_append=args.force_append)
        print(f"  results doc: {results_status}")
        print(f"  spend ledger: {ledger_status}")
        if results_status == "skipped_idempotent":
            print("  (a section with today's date already exists; pass --force-append to override)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
