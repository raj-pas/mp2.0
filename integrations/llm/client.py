from __future__ import annotations

from pydantic import BaseModel


def extract[SchemaT: BaseModel](prompt: str, schema: type[SchemaT]) -> SchemaT:
    """Provider-agnostic structured extraction entrypoint.

    Phase 1 intentionally keeps provider SDKs out of application code.
    """

    raise NotImplementedError("LLM provider wiring lands in Phase 2.")
