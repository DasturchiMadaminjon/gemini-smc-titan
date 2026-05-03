import yaml, warnings, sys
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')
from utils.exchange import ExchangeClient
from core.indicator import GeminiIndicator

with open('config/settings.yaml') as f:
    cfg = yaml.safe_load(f)

ex = ExchangeClient(cfg)
ind = GeminiIndicator(cfg)

symbols = cfg.get('symbols', ['XAU/USD', 'EUR/USD', 'BTC/USDT'])
print('=== SIGNAL TEKSHIRUV ===')
print(f'Min sifat: {cfg["smc"]["min_quality"]}%')
print(f'Timeframe: {cfg.get("timeframe","15m")}')
print(f'Instrumentlar: {len(symbols)} ta')
print('=' * 40)

signal_found = 0
for s in symbols:
    try:
        df = ex.fetch_ohlcv(s, cfg.get('timeframe','15m'), limit=200)
        if df is not None and not df.empty:
            curr_p = float(df['close'].iloc[-1])
            sig = ind.generate_signal(df, s, cfg.get('timeframe','15m'), 0)
            if sig:
                signal_found += 1
                print(f'[SIGNAL] {s} | {sig.direction} | narx={curr_p:.4f} | sifat={int(sig.quality)}% | sabab={sig.reason}')
            else:
                print(f'[EMPTY]  {s} | narx={curr_p:.4f} | signal yoq')
        else:
            print(f'[XATO]   {s} | data yoq')
    except Exception as e:
        print(f'[XATO]   {s} | {type(e).__name__}: {str(e)[:80]}')

print('=' * 40)
print(f'Jami signal: {signal_found} ta | Tekshirildi: {len(symbols)} ta')
