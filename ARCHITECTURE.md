# TITAN V27.2 SMC — Tizim Arxitekturasi 🦾

## 1. Umumiy Arxitektura
Titan V27.2 modulli va asinxron arxitekturaga ega bo'lib, Python 3.9+ va `asyncio` kutubxonasiga asoslangan. Tizim AWS EC2 muhitida 24/7 avtonom ishlashga mo'ljallangan.

## 2. Asosiy Modullar
- **`bot.py`**: Markaziy boshqaruvchi. Skanerlash sikli, Telegram interfeysi va boshqa modullarni bog'laydi.
- **`core/indicator.py`**: Matematik mantiq. OHLCV ma'lumotlarini tahlil qilib, SMC signallarini (BOS, FVG, OB) generatsiya qiladi.
- **`utils/ai_engine.py`**: Vision va Validation. Gemini API orqali signallarni vizual tahlil qiladi va tasdiqlaydi.
- **`utils/exchange.py`**: Ma'lumotlar manbasi. `yfinance` orqali bloklanmagan holda ma'lumotlarni asinxron yuklaydi.
- **`core/manager.py`**: Bitimlarni boshqarish. Risk management, position sizing va natijalarni nazorat qilish.


## 3.1 AI Provayder Arxitekturasi (Sprint 14)
Tizim ikkita AI provayderini qo'llab-quvvatlaydi:
- **Gemini** (default) — GEMINI_API_KEYS orqali
- **Claude** (ixtiyoriy) — CLAUDE_API_KEY orqali

Fail-safe kafolati: Claude xatoga uchrasa yoki kalit yo'q bo'lsa — Gemini avtomatik ishga tushadi.

| O'zgaruvchi | Majburiy | Tavsif |
|-------------|----------|--------|
| GEMINI_API_KEYS | Ha | Vergul bilan ajratilgan Gemini kalitlar |
| CLAUDE_API_KEY | Yo'q | Anthropic Claude kaliti (ixtiyoriy) |

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
- **AI Fail-Safe Fallback**: Claude xatoga uchrasa, Gemini ga avtomatik o'tish (Sprint 14).
- **AI Self-Healing**: AI javobi chala qolsa (missing [TAMOM]), uni avtomatik aniqlash va qayta generatsiya qilish.

## 6. Logging va Monitoring 🪵
- Barcha amallar `logs/` papkasida qayd etiladi.
- Har bir signal uchun unique Hash yaratilib, loglarda kuzatib boriladi.

## 7. Muhim Qoidalar (Invariants) 🔐
- XAU/USD narx ma'lumotlari har doim `GC=F` (Yahoo Finance Gold Futures) tickeridan yuklanadi, chunki `XAUUSD=X` spot delist bo'lgan.
- Foydalanuvchi umumiy chatda biron instrumentni (masalan: XAU/USD, BTC/USDT) so'rasa, bot dinamik ravishda buni aniqlab real-time narxlarni AI promptiga kiritishi shart.
- Har qanday so'rov `auth_manager.py` orqali `access_mode` tekshiruvidan o'tishi shart.

## 8. O'zgarishlar Tarixi
| Sprint 13 | User Management & Access Control | Foydalanuvchilar ro'yxatga olish, whitelist/blacklist, dinamik admin havola va qo'shimcha matn sozlamalari |
| 2026-07-17 | Sprint 14 | Dinamik AI Provayder: Gemini/Claude almashish, fail-safe fallback, Telegram tugmasi |
| Sana | O'zgarish | Muallif |
|------|-----------|---------|
| 2026-05-26 | Umumiy chat fallbackda XAU/USD va boshqa instrumentlar uchun dinamik simbol aniqlash qo'shildi. bot.py dagi 'elif sig:' indent bugi to'g'irlandi. | Antigravity AI |
| 2026-06-04 | Gemini AI takroriy javoblar berishi (unbracketed TAMOM) bartaraf etildi va testlar yangilandi. | Antigravity AI |
| 2026-06-04 | Google Search grounding (internet qidiruvi) AI Engine ga qo'shildi hamda Fundamental tahlil promptidagi query xatosi to'g'irlandi. | Antigravity AI |
| 2026-06-05 | General chat va mentor_qa prompts shartlari optimizatsiya qilindi (OHLC jadvali yo'q bo'lganda DIQQAT ko'rsatmasi yuborilmaydi). | Antigravity AI |

---
*Titan V27.2 - Barqarorlik, Professionalizm va Yuqori Sifat uchun yaratilgan.*
