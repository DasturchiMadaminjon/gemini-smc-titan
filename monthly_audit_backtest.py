"""
monthly_audit_backtest.py
Professional 1-oylik audit (3000 ta sham = ~31 kun). No Emojis for Windows compatibility.
"""
import asyncio
import pandas as pd
import yaml
import os
from datetime import datetime, timezone
from utils.exchange import ExchangeClient
from core.indicator import GeminiIndicator

async def run_full_monthly_audit():
    if not os.path.exists('config/settings.yaml'):
        print("CONFIG TOPILMADI!")
        return
        
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
        
    exchange = ExchangeClient(cfg)
    ind = GeminiIndicator(cfg)
    
    symbols = cfg.get('symbols', [])
    timeframe = cfg.get('timeframe', '15m')
    limit = 3000 
    
    print(f"[FULL AUDIT] 1 OYLIK TAHLIL BOSHLANDI (3000 sham)...")
    print(f"Instrumentlar: {symbols}\n")
    
    total_stats = {
        'total_signals': 0,
        'wins': 0,
        'losses': 0,
        'pending': 0,
        'by_symbol': {}
    }

    for symbol in symbols:
        print(f"Analiz: {symbol}...", end=' ')
        try:
            df = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if df is None or len(df) < 500:
                print(f"SKIP (Ma'lumot kam: {len(df) if df is not None else 0})")
                continue
                
            htf_df = exchange.fetch_ohlcv(symbol, '1h', limit=500)
            sym_signals = []
            
            # Har 5 shamda bir tekshiramiz (step=5) tezlik uchun
            for i in range(200, len(df) - 60, 5):
                sub_df = df.iloc[:i]
                sig = ind.generate_signal(sub_df, symbol, timeframe, loss_streak=0, htf_df=htf_df)
                
                if sig and sig.quality >= 75.0:
                    if sym_signals and (i - sym_signals[-1]['index'] < 30):
                        continue
                        
                    future_df = df.iloc[i:i+60]
                    res = 'PENDING'
                    for _, row in future_df.iterrows():
                        if sig.direction == 'buy':
                            if row['low'] <= sig.sl: res = 'LOSS'; break
                            if row['high'] >= sig.tp1: res = 'WIN'; break
                        else: # sell
                            if row['high'] >= sig.sl: res = 'LOSS'; break
                            if row['low'] <= sig.tp1: res = 'WIN'; break
                    
                    sym_signals.append({'index': i, 'res': res, 'dir': sig.direction})
                    
            s_total = len(sym_signals)
            s_wins = len([s for s in sym_signals if s['res'] == 'WIN'])
            s_losses = len([s for s in sym_signals if s['res'] == 'LOSS'])
            s_pending = len([s for s in sym_signals if s['res'] == 'PENDING'])
            
            total_stats['total_signals'] += s_total
            total_stats['wins'] += s_wins
            total_stats['losses'] += s_losses
            total_stats['pending'] += s_pending
            
            wr = round(s_wins / (s_wins + s_losses) * 100, 1) if (s_wins + s_losses) > 0 else 0
            print(f"DONE | Jami: {s_total} | WIN: {s_wins} | LOSS: {s_losses} | PEND: {s_pending} | WR: {wr}%")
            
            total_stats['by_symbol'][symbol] = {
                'total': s_total, 'wins': s_wins, 'losses': s_losses, 'pending': s_pending, 'wr': wr
            }

        except Exception as e:
            print(f"ERR: {e}")

    print("\n" + "="*60)
    print("1 OYLIK YAKUNIY AUDIT HISOBOTI")
    print("="*60)
    print(f"Jami yuborilgan signallar: {total_stats['total_signals']} ta")
    print(f"Galaba (TP): {total_stats['wins']} ta")
    print(f"Zarar (SL):   {total_stats['losses']} ta")
    print(f"Kutilmoqda:    {total_stats['pending']} ta")
    
    total_closed = total_stats['wins'] + total_stats['losses']
    final_wr = round(total_stats['wins'] / total_closed * 100, 1) if total_closed > 0 else 0
    print(f"Ortacha Win-Rate: {final_wr}%")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(run_full_monthly_audit())
