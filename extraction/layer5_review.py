from __future__ import annotations


def approve_client_state(review_id: str) -> dict:
    """Return the canonical section-approval command shape for a review id."""

    return {
        "review_id": review_id,
        "status": "pending_advisor_approval",
        "required_sections": [
            "household",
            "people",
            "accounts",
            "goals",
            "goal_account_mapping",
            "risk",
        ],
    }
