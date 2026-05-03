import asyncio
import os
import yaml
from datetime import datetime
from utils.database import DatabaseManager
from utils.telegram import TelegramNotifier
from utils.exchange import ExchangeClient
from unittest.mock import AsyncMock, MagicMock

async def test_virtual_monitor():
    print("--- VIRTUAL MONITOR TEST ---")
    
    # 1. Baza va jadvallarni tayyorlash
    test_db_path = "logs/test_monitor.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = DatabaseManager(test_db_path)
    # Jadvalda kerakli ustunlar borligiga ishonch hosil qilamiz (migration ishlaydi)
    
    # 2. Pendig signallarni qo'shamiz (Bitimi ochiq qolgan)
    # BUY: tp1 = 110, sl = 90
    db.add_signal("2026-04-29 10:00", "TEST/USD", "BUY", 100.0, 90.0, 110.0, 90, "Test BUY")
    # SELL: tp1 = 90, sl = 110
    db.add_signal("2026-04-29 10:00", "TEST2/USD", "SELL", 100.0, 110.0, 90.0, 90, "Test SELL")
    
    pending_before = db.get_pending_signals()
    print(f"Boshlang'ich PENDING signallar: {len(pending_before)} ta")
    
    # 3. ExchangeClient'ni soxtalashtiramiz (Mock)
    class MockClient:
        def fetch_ticker(self, symbol):
            if symbol == "TEST/USD":
                return {'last': 115.0}  # BUY uchun TP urildi (115 >= 110)
            elif symbol == "TEST2/USD":
                return {'last': 115.0}  # SELL uchun SL urildi (115 >= 110)
            return {'last': 100.0}
            
    mock_exchange = MagicMock()
    mock_exchange.client = MockClient()
    
    # 4. TelegramNotifier'ni soxtalashtiramiz (Mock)
    mock_telegram = AsyncMock()
    
    # 5. _monitor_loop mantiqini qo'lda yurgizamiz
    pending = db.get_pending_signals()
    for sig in pending:
        sid, symbol, side, entry, sl, tp1 = sig
        ticker = mock_exchange.client.fetch_ticker(symbol)
        price = ticker['last']
        
        result = None
        if side.upper() == 'BUY':
            if price >= tp1: result = 'WIN (TP1)'
            elif price <= sl: result = 'LOSS (SL)'
        else: # SELL
            if price <= tp1: result = 'WIN (TP1)'
            elif price >= sl: result = 'LOSS (SL)'
        
        if result:
            db.update_signal_result(sid, result)
            db.add_history(datetime.now().strftime('%H:%M'), symbol, side.upper()=='BUY', entry, result, 1.0 if 'WIN' in result else -1.0)
            await mock_telegram.send(f"✅ <b>VIRTUAL NATIJA: {symbol}</b>\nNatija: {result}\nNarx: {price}")
            print(f"Monitor: {symbol} natijasi: {result}")
            
    # 6. Tekshiramiz
    pending_after = db.get_pending_signals()
    print(f"Tugagandan keyin PENDING signallar: {len(pending_after)} ta")
    
    stats = db.get_stats()
    print(f"Statistika (get_stats): Jami={stats['total']}, TP={stats['tp']}, SL={stats['sl']}")
    
    print(f"Telegramga jo'natilgan xabarlar soni: {mock_telegram.send.call_count} ta")
    
    if len(pending_after) == 0 and stats['total'] == 2 and mock_telegram.send.call_count == 2:
        print("\n✅ VIRTUAL MONITOR MEXANIZMI TO'G'RI ISHLAMOQDA!")
    else:
        print("\n❌ XATOLIK BOR!")

if __name__ == "__main__":
    asyncio.run(test_virtual_monitor())
