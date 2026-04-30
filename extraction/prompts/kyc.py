"""KYC/profile extraction prompt metadata."""

PROMPT_VERSION = "kyc_review_facts_v1"

CANONICAL_FIELDS = [
    "people[*].display_name",
    "people[*].date_of_birth",
    "people[*].age",
    "people[*].investment_knowledge",
    "accounts[*].regulatory_objective",
    "accounts[*].regulatory_time_horizon",
    "accounts[*].regulatory_risk_rating",
    "risk.household_score",
]
