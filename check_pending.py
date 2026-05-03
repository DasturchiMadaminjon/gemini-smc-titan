from utils.database import DatabaseManager
from utils.exchange import ExchangeClient
import sys, os

sys.path.insert(0, os.path.abspath('.'))

def check():
    db = DatabaseManager()
    pending = db.get_pending_signals()
    print("Pending signals:", len(pending))
    for p in pending:
        print(" ->", p)

    ex = ExchangeClient({'exchange': {'testnet': True, 'name': 'yahoo'}})
    df = ex.fetch_ohlcv('EUR/USD', '1m', limit=2)
    if df is not None and not df.empty:
        print("1m data available, current close:", df['close'].iloc[-1])
    else:
        print("1m data FAILED!")

if __name__ == '__main__':
    check()
