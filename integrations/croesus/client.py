from __future__ import annotations


def get_holdings(client_id: str) -> list[dict]:
    """Return realistic mock holdings until a Croesus API/file adapter exists."""

    return [
        {
            "client_id": client_id,
            "account_id": "mock_account",
            "sleeve_id": "income_fund",
            "sleeve_name": "Income Fund",
            "weight": 0.4,
        },
        {
            "client_id": client_id,
            "account_id": "mock_account",
            "sleeve_id": "equity_fund",
            "sleeve_name": "Equity Fund",
            "weight": 0.6,
        },
    ]
