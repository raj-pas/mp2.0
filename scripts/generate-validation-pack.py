from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.validation_pack import build_validation_pack, markdown_for_validation_pack


def main() -> None:
    output_dir = Path("docs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = build_validation_pack()
    (output_dir / "optimizer_validation.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "optimizer_validation.md").write_text(markdown_for_validation_pack(pack))


if __name__ == "__main__":
    main()
