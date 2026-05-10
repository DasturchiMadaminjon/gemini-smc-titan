# GEMINI SMC TITAN V27.2 - ARCHITECTURE MAP

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
  - **JSON Safety Rule:** API orqali jo'natilayotgan barcha `reply_markup` lar (Inline va Reply klaviaturalar) qat'iyan `json.loads` qilinib, "Object" ko'rinishida yuboriladi (String qilinganda Telegram API "jim" inkor qilmasligi uchun).

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

## 🔄 Fayllar Bog'liqlik Xaritasi (Maintenance Map)

Har qanday faylni o'zgartirganda, quyidagi bog'liqliklarni tekshirish shart:

| Yangilangan Fayl | Birga tekshirilishi kerak | Sababi |
| :--- | :--- | :--- |
| `core/indicator.py` | `tests/test_signal_flow_tdd.py` | Matematik mantiq va signal generation testi. |
| `utils/ai_engine.py` | `tests/test_ai_buttons_logic.py` | AI persona va SDK tahlil qoidalari. |
| `utils/telegram.py` | `tests/test_all_buttons_tdd.py` | UI/UX tugmalar va menyu strukturasi. |
| `utils/exchange.py` | `tests/test_async_integrity.py` | Asinxronlik (Async/Await) va API ulanishlar. |
| `bot.py` | `watchdog.py` | Asosiy tsikl va Heartbeat (yurak urishi). |
| `requirements.txt` | `setup.sh` | Kutubxonalar va virtual muhit barqarorligi. |

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

**ESLATMA (AI VA DASTURCHI UCHUN):** Kod yozishdan oldin ushbu qoidalarni o'qi! Barqarorlik — TDD va Modullilikdadir.
