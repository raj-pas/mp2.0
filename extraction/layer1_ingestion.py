from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawArtifact:
    source_file_id: str
    path: Path
    sha256: str
    source_system: str


def ingest_raw_file(path: Path, *, source_system: str = "manual_file_drop") -> RawArtifact:
    """Register an already-secured raw file as an immutable extraction artifact."""

    resolved = path.resolve()
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return RawArtifact(
        source_file_id=digest,
        path=resolved,
        sha256=digest,
        source_system=source_system,
    )
