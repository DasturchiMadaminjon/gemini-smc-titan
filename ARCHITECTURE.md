# GEMINI SMC TITAN V27.2 - ARCHITECTURE MAP

> **Oxirgi yangilanish:** 2026-05-11 | O'zgartirilgan fayllar: `utils/telegram.py`, `utils/ai_engine.py`, `bot.py`

Ushbu hujjat loyihaning genetik xaritasi va barqarorlik qonunidir.
**QOIDALARNI HECH QACHON BUZMANG!**

---

## 🛡️ 4 TA BARQARORLIK USTUNI (CORE PILLARS)

Loyiha barqarorligini ta'minlash uchun quyidagi 4 ta qoida qat'iy amal qilinishi shart:

1.  **🛡 TDD (Test-Driven Development) - Eng muhim "Xavfsizlik kamari"**
    *   Har qanday yangi funksiya yoki o'zgarishdan avval test yozilishi shart.
    *   Testlar 100% o'tmaguncha kod "tayyor" deb hisoblanmaydi.

2.  **🛰️ Real-Time Context (Fundamental AI Intelligence)**
    *   AI o'z bilim chegarasi bilan cheklanib qolmasligi uchun, unga har doim `NewsWatcher` orqali real vaqtdagi fundamental ma'lumotlar uzatiladi.

3.  **🧩 Modulli Arxitektura (Separation of Concerns)**
    *   Dastur kichik, bir-biriga bog'lanmagan modullardan iborat bo'lishi shart.
    *   `indicator.py` faqat matematika (SMC), `telegram.py` faqat UI/UX.
    *   Modullar o'zaro faqat aniq belgilangan "ko'priklar" (masalan, `bot.py`) orqali muloqot qiladi.

3.  **📝 README va ARCHITECTURE (Yo'l xaritasi)**
    *   Barcha jarayonlar va qoidalar hujjatlashtirilgan bo'lishi shart.
    *   Hujjat koddagi haqiqiy holatni aks ettirishi shart.

4.  **🔄 FSM Auto-Reset (UI/UX Safety)**
    *   Foydalanuvchi adashib "kutish" holatida qolib ketmasligi uchun, har qanday asosiy menyu tugmasi bosilganda barcha eski holatlar (states) avtomatik tozalanadi.
    *   Hujjatlar har doim aktual holatda saqlanishi shart.
    *   Ular nafaqat dasturchi, balki AI uchun ham qat'iy "yo'l xaritasi" vazifasini o'taydi.
    *   O'zgarishlar arxitektura qoidalariga mosligi doimiy tekshiriladi.

4.  **🪵 Loglar (Logging) - Dasturning "Ko'zi"**
    *   Kritik nuqtalarda (signal yuborish, DB yozish, API so'rovlari) loglar bo'lishi shart.
    *   Xatolik yuz berganda loglar orqali muammo kodda yoki tashqi omilda (internet, API) ekanligi darhol aniqlanadi.

---

## 1. MODULLAR TAVSIFI

- **`bot.py` (Master Dvigatel):**
  - Cheksiz tsikl orqali bozorni skaner qiladi.
  - Skaner natijasini `core.indicator` ga berib, signal aniqlaydi.
  - Signal chiqsa, uni `trades.process_and_send_signal` ga yuboradi va orqasidan `print(f"[SIGNAL] {s} yuborildi!")` log yozadi.
  
- **`utils/telegram.py` (UI/UX):**
  - Faqat foydalanuvchi interfeysi, klaviaturalar va API bilan ishlash.
  - `send()` funksiyasi `502, 503, 504` xatoliklarda retry (qayta urinish) mantiqiga ega.
  - Doimo yangi xabar `await self.send()` orqali jo'natiladi.
  - **FSM Symbol Detection (v27.2+):** `in_session` + `module=fundamental` holatida
    foydalanuvchi matni (`SYMBOL_HINTS` lug'ati orqali) tahlil qilinadi va
    `symbol='SMC'` o'rniga haqiqiy instrument (`'XAU/USD'`, `'ETH/USDT'` va h.k.)
    `ai_requests` navbatiga yoziladi. **Bu qoidani BUZMANG** — aks holda AI
    ga `narx=0.00 USD` uzatiladi va generic javob keladi.
  - **JSON Safety Rule:** API orqali jo'natilayotgan barcha `reply_markup` lar (Inline va Reply
    klaviaturalar) qat'iyan `json.loads` qilinib, "Object" ko'rinishida yuboriladi.

- **`core/indicator.py` (SMC Matematikasi):**
  - Bozor strukturasi (FVG, OB, BOS) tahlili.
  - **Dinamik Sifat (Dynamic Quality):** `min_quality` ga asosan ballarni (score) hisoblaydi. Agar sifat < 50% bo'lsa, "Sweep" rejimi faollashadi.

- **`utils/database.py` (Xotira):**
  - Signallar, natijalar (TP/SL) va foydalanuvchi statistikasi.
  - **Deploy tayyorligi:** Kritik ustunlarda (timestamp, symbol, sig_hash) SQLite INDEX lar mavjud.

- **`core/manager.py` (Trade Manager):**
  - Signallarni formatlash, risk menejment (streak protection) va xabarlarni yuborish.
  - `process_and_send_signal` orqali `TelegramNotifier` ga xabar uzatiladi.
  - **Deduplication:** Hash-id orqali 30 daqiqa ichida bir xil signalni takror yubormaslik.
- **`watchdog.py` (Qo'riqchi):**
  - Bot crash bo'lsa yoki muzlab qolsa, restart qiladi va Telegramga ogohlantirish yuboradi.
  - Soatlik restart limiti (MAX_RESTARTS=10) bilan himoyalangan.

---

## 2. STATE MACHINE VA UI MANTIQI

`TelegramNotifier` FSM orqali foydalanuvchi bilan muloqot qiladi:
- `wait_sym_add`: Instrument qo'shish.
- `wait_alert_sym` / `wait_alert_price`: Price Alert o'rnatish.
- `in_session`: Jonli SMC Trener yoki AI Chat Assistant (Multimodal support: matn + rasm + PDF + Word + Excel + CSV + JSON).

---

## 3. PERSISTENSIYA (RESTORE AFTER RESTART)

Bot restart bo'lganda quyidagi ma'lumotlar `data/extras_state.json` orqali qayta tiklanadi:
- `price_alerts`: Foydalanuvchilar o'rnatgan narx bildirishnomalari.
- `dedup_cache`: Takroriy signallarni oldini olish uchun yuborilgan signallar keshi.
- `onboarding_done`: Onboarding ko'rgan foydalanuvchilar ro'yxati.

---

## 4. ANALYTIKA VA AUDIT (PROFESSIONAL TIER)

Bot o'z ichiga quyidagi tahlil vositalarini oladi:
- **`monthly_audit_backtest.py`:** Oxirgi 1 oylik (3000 sham) ma'lumotlar asosida strategiya samaradorligini (Win-Rate, P&L) tahlil qiladi.
- **`watchdog.py` (Heartbeat):** `data/heartbeat.txt` orqali botning tirikligini sekundiga tekshiruvchi avtonom monitoring.
- **`panic_request`:** Favqulodda vaziyatda barcha operatsiyalarni to'xtatuvchi xavfsizlik tugmasi.
- **SQLite Indexes:** Ma'lumotlar bazasining tezkorligi va katta ma'lumotlar (history) bilan ishlashga tayyorligi.

## 🧬 5. GENETIC EVOLUTION ENGINE (GEE) - O'Z-O'ZINI O'STIRISH

Titan V27.2 boti endi oddiy algoritm emas, balki **"O'z-o'zini o'stiruvchi genetik kod"** tamoyili asosida ishlaydi:

1.  **Historical Adaptation (Xotira asosida moslashuv):** 
    - Bot `database.py` dagi signallarning muvaffaqiyatini (`Win/Loss`) kuzatadi.
    - Har 7 kunda "Genetik Audit" o'tkaziladi.
2.  **Parameter Mutation (Parametrlar mutatsiyasi):**
    - Agar Win-rate 60% dan pasaysa, bot `core/indicator.py` dagi SMC parametrlarini (FVG chuqurligi, OB zonalari) `Genetic Engine` orqali +/- 5% ga o'zgartiradi (Mutatsiya).
3.  **Fittest Settings Selection:**
    - Eng yaxshi natija bergan parametrlar yangi "Dominant Gen" sifatida `config/settings.json` ga yoziladi.
4.  **Self-Optimization:** 
    - Bot o'zining `min_quality` filtrini bozorning joriy volatilligiga qarab avtomatik moslashtiradi.

---

## 🔄 Oxirgi O'zgarishlar (Changelog)

### [12.05.2026] - Data Source Migratsiyasi & AWS Fix
- **Exchange Migration**: Binance API AWS EC2 IP-larini bloklagani sababli (`400 Bad Request`), barcha ma'lumot olish tizimi `yfinance` (Yahoo Finance) ga ko'chirildi.
- **Instrument Coverage**: Endi Oltin (GC=F), Forex (EURUSD=X) va Kripto (BTC-USD) bir xil ishonchli manbadan olinadi.
- **Quality Logic Fix**: Telegram menyusi orqali sifatni 50% ga tushirish `settings.yaml` ga yozilishi va `bot.py` tomonidan har siklda o'qilishi ta'minlandi.
- **TDD Pass**: Barcha zanjirli testlar yangi `ExchangeClient` bilan muvaffaqiyatli o'tdi.

### [11.05.2026] - Fundamental AI & Symbol Detection
- **FSM Symbol Detection**: Foydalanuvchi matnidan instrumentni (masalan, "gold" -> "XAU/USD") aniqlash mantiqi qo'shildi.
- **Price Fallback**: Agar xotirada narx bo'lmasa, AI tahlili uchun narx avtomatik ravishda `price_fetcher` orqali olinadi.
- **Persona Engineering**: Fundamental AI tahlili uchun qat'iy format (INSTRUMENT, NARX, BIAS...) joriy etildi.

---

## 🔄 Fayllar Bog'liqlik Xaritasi (Yangilangan)

| Yangilangan Fayl | Birga tekshirilishi kerak | Sababi |
| :--- | :--- | :--- |
| `utils/exchange.py` | `bot.py`, `tests/test_logic.py` | Data manbai o'zgarsa, barcha skanerlar tekshiriladi. |
| `core/indicator.py` | `tests/test_signal_flow_tdd.py` | Matematik mantiq test bilan tasdiqlanishi shart. |
| `utils/telegram.py` | `tests/test_all_buttons_tdd.py` | UI o'zgarsa, test ham o'zgaradi. |
| `bot.py` | `watchdog.py`, `ARCHITECTURE.md` | Asosiy sikl o'zgarsa, heartbeat va xarita yangilanadi. |
| `utils/price_fetcher.py` | `tests/test_fundamental_symbol_detection.py` | Narx olish fallback mantiq — `narx=0` muammosi. |

---

## ⚠️ Texnik Qarzdorlik va Ogohlantirishlar (Technical Debt)

2026-yil 12-maydagi 203 ta test natijasiga ko'ra quyidagilar qayd etildi:

1. **AI SDK Yangilanishi**: Hozirda `google-generativeai` ishlatilmoqda. Google ushbu paketni qo'llab-quvvatlashni to'xtatgan. Kelgusida tizimni yangi `google.genai` (V1) SDK-ga o'tkazish tavsiya etiladi.
2. **Python 3.14 Mosligi**: Ayrim ichki kutubxonalar (`httplib2`) yangi Python versiyasida `DeprecationWarning` bermoqda. Bu hozirgi ishlashga ta'sir qilmaydi, lekin kutubxonalarni vaqti-vaqti bilan yangilab turish shart.
3. **Data Throttling**: `yfinance` ommaviy API bo'lgani uchun, juda ko'p (masalan, 50+ instrument) so'rov yuborilsa, vaqtinchalik limitga tushishi mumkin. Hozirgi 13 ta instrument uchun bu xavfsiz.

---

> [!IMPORTANT]
> **Keyingi qadamlar:**
> 1. Har doim `python -m pytest` yurgizish.
> 2. `logs/watchdog.log` orqali jonli nazorat qilish.
> 3. Yangi instrument qo'shilsa, `utils/exchange.py` dagi `SYMBOL_MAP` ni yangilash.

## ⚡️ Asinxronlik Qoidalari (Async Engine Rules)

Loyiha to'liq `asyncio` ga o'tkazildi. Bloklanishlarning (freezing) oldini olish uchun:
1. **Blocking funksiyalar taqiqlanadi:** `requests`, `time.sleep`, `os.system` kabi sinxron chaqiriqlar o'rniga `aiohttp`, `asyncio.sleep` va `run_in_executor` ishlatilishi shart.
2. **AI Engine Threading:** Google Gemini (yoki boshqa AI SDK lar) qancha kutishidan qat'iy nazar, ular faqat va faqat `await asyncio.to_thread(chat.send_message)` orqali alohida jarayonda chaqirilishi shart. Event loop band qilinmaydi!
3. **Heartbeat monitoring:** `bot.py` har bir skanerlash tsikli oxirida `data/heartbeat.txt` faylini yangilaydi. `watchdog.py` buni kuzatib boradi.
4. **TDD Integrity:** Har bir yangi API integratsiyasi `tests/test_async_integrity.py` orqali tekshirilishi shart.

## 🛡 TDD va Himoya Qatlamlari
1. **Unit Tests:** Funksiyalar mantig'i.
2. **Integration Tests:** Modullararo aloqa (Mock-siz).
3. **Async Integrity:** Event loop bloklanmasligi kafolati.

---

## 📋 O'ZGARISHLAR TARIXI (CHANGELOG)

### 2026-05-11 — Fundamental AI Tuzatish (Muammo: narx=0, symbol=SMC)

**Muammo:** Foydalanuvchi "goldni analiz qil" yozganda:
1. `symbol='SMC'` hardcoded → AI ga noto'g'ri instrument uzatilgan
2. `price=0.0` → `bot_state['symbols']` da `SMC` yo'qligi sababli narx 0 bo'lgan
3. Fundamental persona generic makro ma'ruza yozgan (format yo'q edi)

**Tuzatishlar:**
- `utils/telegram.py` → `in_session` + `fundamental` uchun `SYMBOL_HINTS` lug'ati qo'shildi
- `bot.py` → `price=0` bo'lganda `price_fetcher.get_current_price()` fallback ishlaydi
- `utils/ai_engine.py` → Fundamental persona qat'iy 6-bo'limli format bilan yangilandi

**Yangi test:** `tests/test_fundamental_symbol_detection.py`
- 25 ta test, 4 ta sinf: Symbol Detection, AI Request Queue, Persona Format, Price Fallback
- **Flake8: 0 xato** (clean code standartlari bajarildi)
- Barcha 25 test: ✅ PASSED

---

**ESLATMA (AI VA DASTURCHI UCHUN):** Kod yozishdan oldin ushbu qoidalarni o'qi!
Barqarorlik — TDD va Modullilikdadir.
