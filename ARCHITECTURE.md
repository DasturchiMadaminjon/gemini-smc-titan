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

- **`core/indicator.py` (SMC Matematikasi):**
  - Bozor strukturasi (FVG, OB, BOS) tahlili. Tashqi dunyo haqida hech narsa bilmaydi.

- **`utils/database.py` (Xotira):**
  - Signallar, natijalar (TP/SL) va foydalanuvchi statistikasi.
  - **Deploy tayyorligi:** Kritik ustunlarda (timestamp, symbol, sig_hash) SQLite INDEX lar mavjud.

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

---

**ESLATMA (AI VA DASTURCHI UCHUN):** Kod yozishdan oldin ushbu qoidalarni o'qi! Barqarorlik — TDD va Modullilikdadir.
