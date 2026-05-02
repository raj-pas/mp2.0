"""Pre-upload a real-PII client folder for demo prep.

Usage:
    uv run python scripts/demo-prep/upload_and_drain.py <client_name>

Example:
    uv run python scripts/demo-prep/upload_and_drain.py Seltzer
    uv run python scripts/demo-prep/upload_and_drain.py Weryha

Creates a `real_derived` review workspace, uploads every supported
file in `${CLIENTS_ROOT}/<client_name>/` via Python `requests` (which
handles all filename shapes that broke `curl -F` during the R10 sweep),
spawns a `process_review_queue` worker, polls until every doc reaches
a terminal status, then prints the final demo state.

Source folder: ``/Users/saranyaraj/Documents/MP2.0_Clients/<client_name>``.
All files with these extensions are uploaded: .pdf .docx .xlsx .csv
.txt .md.

Requires:
  - Django dev server reachable at API_BASE
  - MP20_LOCAL_ADMIN_PASSWORD env var set (for advisor login)
  - .env loaded so the worker has Bedrock + DATABASE_URL + secure root

Real-PII discipline (canon §11.8.3): only structural counts go to
stdout. No client content is logged, quoted, or persisted outside the
secure root.

Replaces the prior /tmp/demo-prep-seltzer.py script — durable repo
copy survives reboots and is version-controlled. Lives under
scripts/demo-prep/ alongside any future per-client demo helpers.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"
CLIENTS_ROOT = Path("/Users/saranyaraj/Documents/MP2.0_Clients")
SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}
PROJECT_ROOT = Path("/Users/saranyaraj/Projects/github-repo/mp2.0")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "client_name",
        help="Folder name under MP2.0_Clients/ (e.g., Seltzer, Weryha)",
    )
    parser.add_argument(
        "--expect-count",
        type=int,
        default=None,
        help=(
            "Expected document count for the demo OK assertion. If "
            "omitted, accepts any count where reconciled == total and "
            "failed == 0."
        ),
    )
    args = parser.parse_args()

    client_root = CLIENTS_ROOT / args.client_name
    if not client_root.is_dir():
        raise SystemExit(f"Client folder not found: {client_root}")

    label = f"{args.client_name} review (demo prep)"
    print(f"=== Demo prep: {args.client_name} pre-upload ===")

    s = login()
    csrf = s.cookies.get("csrftoken")
    r = s.post(
        f"{API_BASE}/api/review-workspaces/",
        json={"label": label, "data_origin": "real_derived"},
        headers={"X-CSRFToken": csrf, "Referer": API_BASE},
    )
    r.raise_for_status()
    wsid = r.json()["external_id"]
    print(f"  workspace external_id: {wsid}")

    csrf = s.cookies.get("csrftoken")
    files_uploaded = 0
    for path in sorted(client_root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        with open(path, "rb") as fh:
            r = s.post(
                f"{API_BASE}/api/review-workspaces/{wsid}/upload/",
                files={"files": (path.name, fh)},
                headers={"X-CSRFToken": csrf, "Referer": API_BASE},
                timeout=60,
            )
        r.raise_for_status()
        body = r.json()
        files_uploaded += len(body.get("uploaded", []))
    print(f"  files uploaded: {files_uploaded}")

    print(f"\n=== Worker drain ({args.client_name} through Bedrock) ===")
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
        env={
            **os.environ,
            "DATABASE_URL": "postgres://mp20:mp20@localhost:5432/mp20",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"  worker PID: {proc.pid}")

    # Poll until queue drains (max ~7.5 min @ 15s polls × 30 iters)
    for i in range(30):
        time.sleep(15)
        r = s.get(f"{API_BASE}/api/review-workspaces/{wsid}/")
        r.raise_for_status()
        d = r.json()
        doc_statuses: dict[str, int] = {}
        for doc in d.get("documents", []):
            doc_statuses[doc["status"]] = doc_statuses.get(doc["status"], 0) + 1
        job_statuses: dict[str, int] = {}
        for job in d.get("processing_jobs", []):
            job_statuses[job["status"]] = job_statuses.get(job["status"], 0) + 1
        active_jobs = job_statuses.get("queued", 0) + job_statuses.get("processing", 0)
        print(f"  [{i + 1:>2}] doc statuses={doc_statuses} jobs active={active_jobs}")
        if active_jobs == 0:
            break

    # Stop worker
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Final state
    r = s.get(f"{API_BASE}/api/review-workspaces/{wsid}/")
    r.raise_for_status()
    d = r.json()
    docs = d.get("documents", [])
    reconciled = sum(1 for x in docs if x["status"] == "reconciled")
    failed = sum(1 for x in docs if x["status"] == "failed")
    print("\n=== Final demo state ===")
    print(f"  workspace status: {d['status']}")
    print(f"  reconciled: {reconciled} | failed: {failed} | total: {len(docs)}")
    print(f"  required_sections: {d.get('required_sections')}")
    print(f"  readiness: {d.get('readiness')}")
    state = d.get("reviewed_state") or {}
    print(
        f"  state: people={len(state.get('people') or [])} "
        f"accounts={len(state.get('accounts') or [])} "
        f"goals={len(state.get('goals') or [])} "
        f"conflicts={len(state.get('conflicts') or [])}"
    )

    expected = args.expect_count
    ok_count = reconciled == expected if expected is not None else reconciled == len(docs)
    if not ok_count or failed != 0:
        print(
            f"\nWARNING: not {expected if expected else len(docs)}/"
            f"{len(docs)} reconciled — investigate before demo"
        )
        return 1
    print(f"\nOK {args.client_name} {reconciled}/{len(docs)} reconciled, ready for demo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
