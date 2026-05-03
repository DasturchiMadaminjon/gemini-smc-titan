import asyncio, yaml
from utils.exchange import ExchangeClient
from core.indicator import GeminiIndicator

async def run_historical_test():
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
        
    exchange = ExchangeClient(cfg)
    ind = GeminiIndicator(cfg)
    
    symbols = cfg['symbols']
    timeframe = cfg.get('timeframe', '15m')
    
    # Kengroq ko'rish uchun ko'proq sham olamiz (1000 ta sham = ~10 kun)
    limit = 1000
    
    print(f"[TEST] Barcha {len(symbols)} ta instrument uchun chuqur TARIXIY test boshlandi.")
    print(f"       TF: {timeframe} | Qamrov: oxirgi {limit} ta sham (taxminan 10 kun)\n")
    
    found_signals = 0
    total_analyzed = 0
    
    for s in symbols:
        try:
            df = exchange.fetch_ohlcv(s, timeframe, limit=limit)
            if df is None or df.empty:
                print(f"[SKIP] {s} ma'lumot yuklab bo'lmadi.")
                continue
                
            # HTF Trend olish (1H)
            htf_df = None
            try:
                htf_df = exchange.fetch_ohlcv(s, '1h', limit=300)
            except: pass
            
            sig = ind.generate_signal(df, s, timeframe, loss_streak=0, htf_df=htf_df)
            total_analyzed += 1
            
            if sig:
                # Agar sifat 50% dan yuqori bo'lsa (Dvigatel qanday ishlashini ko'rsatish uchun)
                if sig.quality >= 50.0:
                    status = "✅ O'TDI (A+ Sifat)" if sig.quality >= 75.0 else "⚠️ O'RTA SIFAT (Filtirda qoladi)"
                    print(f"[{status}] {s} -> YO'NALISH: {sig.direction} | SIFAT: {sig.quality}%")
                    print(f"       KIRISH: {sig.entry:.4f} | SL: {sig.sl:.4f} | TP1: {sig.tp1:.4f}")
                    print(f"       ASOS: {sig.reason}")
                    print("-" * 50)
                    found_signals += 1
                else:
                    print(f"[FILTERED] {s} da signal bor, lekin sifati juda past ({sig.quality}%).")
            else:
                print(f"[NO SIGNAL] {s} da hech qanday SMC strukturasi topilmadi.")
                
        except Exception as e:
            print(f"[ERROR] {s}: {e}")
            
    print(f"\n[XULOSA] {total_analyzed} ta instrument tahlil qilindi.")
    print(f"Hosil bo'lgan potensial signallar soni: {found_signals} ta")

if __name__ == '__main__':
    asyncio.run(run_historical_test())
