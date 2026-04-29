from __future__ import annotations

from pathlib import Path


def test_runtime_surfaces_do_not_use_legacy_cma_labels() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "engine",
        root / "web",
        root / "frontend/src",
        root / "frontend/e2e",
        root / "docker-compose.yml",
    ]
    blocked = ["Fra" + "ser", "fra" + "ser", "mp20_" + "scenario_evaluator", "draft" + " draft"]
    offenders: list[str] = []
    for path in paths:
        files = [path] if path.is_file() else path.rglob("*")
        for file_path in files:
            if not file_path.is_file() or file_path.suffix in {".pyc", ".png", ".jpg"}:
                continue
            text = file_path.read_text(errors="ignore")
            for pattern in blocked:
                if pattern in text:
                    offenders.append(str(file_path.relative_to(root)))
                    break

    assert offenders == []
