from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawArtifact:
    source_file_id: str
    path: Path
    sha256: str
    source_system: str


def ingest_raw_file(path: Path, *, source_system: str = "manual_file_drop") -> RawArtifact:
    """Phase 1 interface stub for immutable raw ingestion."""

    raise NotImplementedError("Raw ingestion lands in Phase 2.")
