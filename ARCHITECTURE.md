# TITAN V27.2 SMC — Tizim Arxitekturasi 🦾

## 1. Umumiy Arxitektura
Titan V27.2 modulli va asinxron arxitekturaga ega bo'lib, Python 3.9+ va `asyncio` kutubxonasiga asoslangan. Tizim AWS EC2 muhitida 24/7 avtonom ishlashga mo'ljallangan.

## 2. Asosiy Modullar
- **`bot.py`**: Markaziy boshqaruvchi. Skanerlash sikli, Telegram interfeysi va boshqa modullarni bog'laydi.
- **`core/indicator.py`**: Matematik mantiq. OHLCV ma'lumotlarini tahlil qilib, SMC signallarini (BOS, FVG, OB) generatsiya qiladi.
- **`utils/ai_engine.py`**: Vision va Validation. Gemini API orqali signallarni vizual tahlil qiladi va tasdiqlaydi.
- **`utils/exchange.py`**: Ma'lumotlar manbasi. `yfinance` orqali bloklanmagan holda ma'lumotlarni asinxron yuklaydi.
- **`core/manager.py`**: Bitimlarni boshqarish. Risk management, position sizing va natijalarni nazorat qilish.

## 3. Asinxron Butunlik (Async Integrity) ⚡
Tizimning barcha CPU-intensive va I/O amallari blocking bo'lmasligi shart:
- Tarmoq so'rovlari (`yfinance`) alohida `run_in_executor` poolda bajariladi.
- Grafik chizish (`matplotlib`) event loopni bloklamasligi uchun fonda ishlaydi.
- Har bir modul `tests/test_async_integrity_tdd.py` orqali tekshiriladi.

## 4. TDD (Test-Driven Development) — Xavfsizlik Kamari 🛡
Har bir yangi funksiya quyidagi qatlamlar orqali o'tadi:
1. **Unit Tests**: Alohida funksiyalarni tekshirish.
2. **Integration Tests**: Modullararo aloqani tekshirish.
3. **Async Integrity Tests**: Asinxron butunlikni tasdiqlash.

## 5. Xatoliklarga chidamlilik (Resilience)
- **Watchdog**: Bot to'xtab qolsa, uni 30 soniya ichida qayta ishga tushiradi.
- **Deduplication**: Bir xil signallar 30 daqiqa ichida qayta yuborilishi bloklanadi.
- **Smart Chunking**: Telegram'ning 4000 belgilik limiti uchun aqlli (abzaslar bo'yicha) bo'laklash tizimi.
- **HTML Sanitization**: AI javoblaridagi maxsus belgilarni (&, <, >) Telegram HTML parseri uchun avtomatik escape qilish.
- **AI Self-Healing**: AI javobi chala qolsa (missing [TAMOM]), uni avtomatik aniqlash va qayta generatsiya qilish.

## 6. Logging va Monitoring 🪵
- Barcha amallar `logs/` papkasida qayd etiladi.
- Har bir signal uchun unique Hash yaratilib, loglarda kuzatib boriladi.

---
*Titan V27.2 - Barqarorlik, Professionalizm va Yuqori Sifat uchun yaratilgan.*
