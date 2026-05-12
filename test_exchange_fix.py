import asyncio, sys, yaml
sys.path.insert(0, '.')
from utils.exchange import ExchangeClient

async def test():
    with open('config/settings.yaml') as f:
        cfg = yaml.safe_load(f)
    ex = ExchangeClient(cfg)
    symbols = ['XAU/USD', 'EUR/USD', 'GBP/USD', 'BTC/USDT', 'ETH/USDT', 'USD/JPY', 'SOL/USDT']
    passed = 0
    for s in symbols:
        df = await ex.fetch_ohlcv(s, '15m', limit=200)
        if df is not None and len(df) >= 50:
            price = df['close'].iloc[-1]
            print(f"OK  {s:15s} -> {len(df)} sham | narx={price:.4f}")
            passed += 1
        else:
            print(f"ERR {s:15s} -> DATA YOQ")
    print(f"\nNatija: {passed}/{len(symbols)} instrument ishlaydi")

asyncio.run(test())
