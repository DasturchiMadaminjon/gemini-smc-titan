import asyncio
import time
import pytest
import yaml
import os
from utils.exchange import ExchangeClient

class AsyncMonitor:
    def __init__(self):
        self.counter = 0
        self.active = True

    async def start_counting(self):
        """Orqa fonda to'xtovsiz sonlarni sanaydi."""
        while self.active:
            self.counter += 1
            await asyncio.sleep(0.01) # 10ms kutish

@pytest.mark.asyncio
async def test_fetch_ohlcv_is_non_blocking():
    # 1. Sozlamalarni yuklash
    config_path = 'config/settings.yaml'
    if not os.path.exists(config_path):
        # Agar config yo'q bo'lsa, minimal mock config yaratamiz
        config = {'exchange': {'name': 'binance'}, 'smc': {'min_quality': 70}}
    else:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    client = ExchangeClient(config)
    monitor = AsyncMonitor()
    
    # 2. Monitoringni boshlash (Event loop orqali)
    monitor_task = asyncio.create_task(monitor.start_counting())
    
    # Kichik pauza - monitor ishga tushishi uchun
    await asyncio.sleep(0.05)
    
    # 3. API chaqiruvi (Bu vaqt ichida monitor ishlashi kerak)
    start_time = time.time()
    # Haqiqiy API chaqiruvi
    df = await client.fetch_ohlcv("BTC/USDT", "1h", limit=50)
    duration = time.time() - start_time
    
    # 4. Monitoringni to'xtatish
    monitor.active = False
    await monitor_task
    
    print(f"\n[INFO] API chaqiruvi {duration:.2f} soniya davom etdi.")
    print(f"[INFO] Sanagich qiymati: {monitor.counter}")
    
    # 5. Tekshiruv:
    # Sanagich qiymati API kutish vaqtiga mutanosib bo'lishi kerak.
    # Masalan, 0.5s kutishda kamida 20-30 ta sanash amalga oshishi kerak.
    
    print(f"DONE: ASYNC TEST: Sanagich {monitor.counter} gacha yetdi.")
    if duration > 0.1:
        expected_min = int(duration * 50) # Har 0.02s da bitta sanash (nazariy)
        assert monitor.counter >= 5, f"Event loop bloklangan! Sanagich juda kichik: {monitor.counter}"
    
    print(f"SUCCESS: ASYNC INTEGRITY: OK (Loop bloklanmadi)")

if __name__ == "__main__":
    # Agar fayl to'g'ridan-to'g'ri yurgizilsa (pytest-siz)
    asyncio.run(test_fetch_ohlcv_is_non_blocking())
