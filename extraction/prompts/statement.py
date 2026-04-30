"""Statement/account extraction prompt metadata."""

PROMPT_VERSION = "statement_review_facts_v1"

CANONICAL_FIELDS = [
    "accounts[*].account_type",
    "accounts[*].current_value",
    "accounts[*].account_number",
    "accounts[*].holdings",
    "accounts[*].missing_holdings_confirmed",
]
