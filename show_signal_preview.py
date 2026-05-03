"""
tests/show_signal_preview.py
Botdan keladigan signal ko'rinishini Telegram formatsiyasida ko'rsatib berish.
"""
from core.indicator import Signal
from utils.position_sizer import format_position_line

def show_preview():
    # 1. Boshlang'ich test signal ma'lumotlari yaratish (Oddiy long vaziyat)
    sig = Signal(
        direction='buy',
        symbol='XAU/USD',
        entry=2350.50,
        sl=2340.00,
        tp1=2365.00,
        tp2=2380.00,
        tp3=2410.00,
        quality=85.0,
        reason="SMC BOS UP + FVG + Fibo 0.618",
        timestamp=None
    )
    
    # 2. Risk - position hisoblash test line
    pos_line = "Lot: 0.12 | Risk: $100 (2%)"
    
    # 3. Telegram formatida msg log tayyorlash
    direction_str = "BUY (LONG)" if sig.direction == 'buy' else "SELL (SHORT)"
    e2 = sig.entry - (sig.entry - sig.sl) * 0.382
    
    msg  = f"YANGI SIGNAL: {sig.symbol}\n"
    msg += f"--------------------\n"
    msg += f"Signal: {direction_str}\n"
    msg += f"Sifat: {sig.quality:.1f}%\n\n"
    msg += f"1-Kirish: {sig.entry:.5g}\n"
    msg += f"2-Kirish: {e2:.5g}\n"
    msg += f"Stop-Loss: {sig.sl:.5g}\n\n"
    msg += f"Maqsadlar:\n"
    msg += f"   1. TP1: {sig.tp1:.5g}\n"
    msg += f"   2. TP2: {sig.tp2:.5g}\n"
    msg += f"   3. TP3: {sig.tp3:.5g}\n\n"
    msg += f"Asos: {sig.reason}\n"
    msg += f"--------------------\n"
    msg += pos_line + "\n"
    msg += f"--------------------\n"
    msg += f"Titan V27.2 Master"
    
    print("--- TELEGRAM XABARI KO'RINISHI ---")
    print(msg)
    print("----------------------------------")

if __name__ == "__main__":
    show_preview()
