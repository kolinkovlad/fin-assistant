from collections import defaultdict

from app.data.load import load_portfolio_data

latest_seen = defaultdict(lambda: ('1970-01-01T00:00:00', 0.0))

portfolio_data = load_portfolio_data()

for tx in portfolio_data['transactions']:
    isin = tx['isin']
    ts = tx['timestamp']
    price = tx['price']
    if ts > latest_seen[isin][0]:
        latest_seen[isin] = (ts, price)

latest_prices = {isin: price for isin, (ts, price) in latest_seen.items()}
