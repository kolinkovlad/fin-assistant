import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # points to `app/`


def load_json(relative_path: str):
    file_path = BASE_DIR / relative_path
    with open(file_path, 'r') as f:
        return json.load(f)


def load_portfolio_data():
    return {
        "holdings": load_json('data/holdings.json'),
        "cash_balances": load_json('data/cash_balances.json'),
        "accounts": load_json('data/accounts.json'),
        "fund_metadata": load_json('data/fund_metadata.json'),
        "transactions": load_json('data/mock_transactions.json'),
    }
