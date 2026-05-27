import asyncio
import yaml
import pandas as pd
from utils.exchange import ExchangeClient
from core.indicator import GeminiIndicator

async def analyze_market():
    print("=== LIVE SMC MARKET QUANT AUDIT START ===")
    
    # Load configuration
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    
    exchange = ExchangeClient(cfg)
    ind = GeminiIndicator(cfg)
    
    min_q = cfg.get('smc', {}).get('min_quality', 75.0)
    print(f"Timeframe: {cfg.get('timeframe', '15m')} | Min Quality Threshold: {min_q}%\n")
    
    symbols = cfg.get('symbols', [])
    
    for s in symbols:
        print(f"Analyzing {s}...")
        try:
            # Fetch TF (e.g. 15m) and HTF (1h)
            df = await exchange.fetch_ohlcv(s, cfg.get('timeframe', '15m'), limit=200)
            htf_df = await exchange.fetch_ohlcv(s, '1h', limit=250)
            
            if df is None or df.empty:
                print(f"[ERROR] {s}: Failed to fetch timeframe data.")
                continue
            
            curr_p = float(df['close'].iloc[-1])
            print(f"  Current Price: {curr_p}")
            
            # Check structure breaks (BOS / Sweep)
            struct = ind._detect_structure_break(df)
            print(f"  Structure Breaks: BOS_UP={struct['bos_up']}, BOS_DOWN={struct['bos_down']}, SWEEP_UP={struct['sweep_up']}, SWEEP_DOWN={struct['sweep_down']}")
            
            # Check Trend, Zone, and FVG
            htf_trend = ind._get_trend(htf_df) if htf_df is not None else 'neutral'
            recent_high = df['high'].rolling(100).max().iloc[-1]
            recent_low = df['low'].rolling(100).min().iloc[-1]
            zone = ind._get_fibo_zone(recent_low, recent_high, curr_p)
            fvgs = ind._find_unmitigated_fvg(df.tail(100))
            
            print(f"  HTF Trend (1h): {htf_trend}")
            print(f"  Fibonacci Zone: {zone} (Range: {recent_low:.5g} - {recent_high:.5g})")
            print(f"  FVGs: Bullish FVG={fvgs['bullish'] is not None}, Bearish FVG={fvgs['bearish'] is not None}")
            
            # Evaluate using generate_signal
            sig = ind.generate_signal(df, s, cfg.get('timeframe', '15m'), loss_streak=0, htf_df=htf_df)
            
            if sig:
                print(f"  [SIGNAL FOUND] {sig.direction.upper()} | Quality: {sig.quality}%")
                print(f"    Entry: {sig.entry:.5g} | SL: {sig.sl:.5g} | TP1: {sig.tp1:.5g}")
                if sig.quality >= min_q:
                    print(f"    [OK] Quality matches threshold! This would be SENT.")
                else:
                    print(f"    [SKIP] Quality ({sig.quality}%) is below threshold ({min_q}%). SKIPPED.")
            else:
                print(f"  [INFO] No structure break setup matches on the current candle.")
                
        except Exception as e:
            print(f"[ERROR] Error analyzing {s}: {e}")
            
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(analyze_market())
