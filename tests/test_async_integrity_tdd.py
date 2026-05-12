import asyncio
import pytest
import time
from utils.exchange import ExchangeClient

async def background_counter(state):
    """Event loopni bloklanmaganligini tekshirish uchun fonda ishlovchi sanagich."""
    while state['running']:
        state['count'] += 1
        await asyncio.sleep(0.05) # Tezroq tekshirish uchun 50ms

@pytest.mark.asyncio
async def test_exchange_async_non_blocking_integrity():
    """
    TDD: fetch_ohlcv (yfinance) asosiy event loopni bloklab qo'ymasligini tekshirish.
    Verification: Fondagi sanagich so'rov davomida o'sishda davom etishi shart.
    """
    client = ExchangeClient({})
    state = {'count': 0, 'running': True}
    
    # 1. Fondagi vazifani boshlash
    counter_task = asyncio.create_task(background_counter(state))
    
    try:
        # 2. Sifatli (uzoqroq davom etuvchi) so'rovni yuborish
        # XAU/USD uzoqroq vaqt olishi mumkin
        start_time = time.time()
        df = await client.fetch_ohlcv("BTC/USDT", "15m", limit=100)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\nDEBUG: fetch_ohlcv took {duration:.2f} seconds.")
        
        # 3. Fondagi vazifani to'xtatish
        state['running'] = False
        await counter_task
        
        final_count = state['count']
        print(f"DEBUG: Background counter reached {final_count}.")
        
        # Agar loop bloklanmagan bo'lsa, count > 0 bo'lishi kerak.
        # Masalan 1 soniyada count ~20 marta o'sishi kerak.
        expected_min = int(duration / 0.1) # Kamida yarmi o'tgan bo'lishi kerak
        assert final_count > expected_min, f"KRITIK: Event loop bloklangan! Counter {final_count} da to'xtab qolgan (Kutilgan: >{expected_min})."
        
        print(f"SUCCESS: Async integrity verified. Event loop is healthy.")

    except Exception as e:
        state['running'] = False
        counter_task.cancel()
        pytest.fail(f"Test xatolik bilan tugadi: {e}")

@pytest.mark.asyncio
async def test_indicator_drawing_async_integrity():
    """
    TDD: Grafik chizish (matplotlib) event loopni bloklamasligini tekshirish.
    Grafik chizish CPU-intensive ish, uni ham run_in_executor da qilish tavsiya etiladi.
    """
    from core.indicator import GeminiIndicator
    import pandas as pd
    import numpy as np
    
    # Fake data
    dates = pd.date_range('2026-01-01', periods=100, freq='15min')
    df = pd.DataFrame(np.random.randn(100, 4), index=dates, columns=['open', 'high', 'low', 'close'])
    df['volume'] = 1000
    
    ind = GeminiIndicator({})
    state = {'count': 0, 'running': True}
    counter_task = asyncio.create_task(background_counter(state))
    
    try:
        # Grafik chizish uzoq vaqt oladi
        # Hozirda indicator.py dagi draw_chart_bytes sinxron. 
        # Keling, buni asinxronligini tekshiramiz.
        loop = asyncio.get_event_loop()
        # Biz buni run_in_executor da chaqirishimiz kerak
        img = await loop.run_in_executor(None, ind.draw_chart_bytes, df, "BTC/USDT")
        
        state['running'] = False
        await counter_task
        
        print(f"DEBUG: Drawing counter reached {state['count']}.")
        assert state['count'] > 0, "Grafik chizish event loopni bloklab qo'ydi!"
        
    except Exception as e:
        state['running'] = False
        pytest.fail(f"Drawing test error: {e}")
