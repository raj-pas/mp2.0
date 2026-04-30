"""Meeting-note extraction prompt metadata.

Meeting notes are split into factual extraction and behavioral synthesis.
Behavioral context must stay under `behavioral_notes.*` unless an advisor maps
it to a canonical engine/review field.
"""

PROMPT_VERSION = "meeting_note_review_facts_v1"
