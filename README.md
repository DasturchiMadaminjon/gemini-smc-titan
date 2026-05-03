# GEMINI SMC TITAN V27.2 A+ MASTER ENGINE

Ushbu dastur Smart Money Concepts (SMC) strategiyasi asosida ishlaydigan, 24/7 avtonom treyding boti va yordamchisidir. U bozor ma'lumotlarini tahlil qiladi, AI (Gemini) yordamida signallarni tasdiqlaydi va foydalanuvchiga Telegram orqali etkazib beradi.

---

## 🚀 ASOSIY TAMOYILLAR (STABILITY PILLARS)

Dastur quyidagi 4 ta ustun ustiga qurilgan:
1.  **🛡 TDD (100% Test Coverage):** Har bir o'zgarish `pytest` orqali tekshirilgan.
2.  **🧩 Modullilik:** Har bir modul (Signal, UI, AI, DB) mustaqil ishlaydi.
3.  **📝 Hujjatlar:** `ARCHITECTURE.md` va `README.md` — barcha jarayonlar uchun yagona manba.
4.  **🪵 Loglar:** Bot harakati va xatolar real vaqtda loglanadi.

---

## 🛠 TEXNOLOGIK STEK
- **Python 3.11+**
- **Kutubxonalar:** `aiohttp`, `ccxt`, `google-generativeai`, `pandas`, `PyPDF2`, `python-docx`, `pytest`.
- **Baza:** SQLite (Optimallashtirilgan INDEX lar bilan).
- **Muhit:** Local (Windows/Mac) yoki AWS EC2 (Linux).

---

## ⚙️ O'RNATISH (INSTALLATION)

### 1. Muhitni sozlash (.env)
`.env` fayliga kalitlarni yozing:
```env
GEMINI_API_KEY=AIzaSyA...
TELEGRAM_BOT_TOKEN=867232...
```

### 2. Ishga tushirish (Watchdog bilan)
Dasturning barqarorligini `watchdog.py` ta'minlaydi:
```bash
# Botni monitoring bilan ishga tushirish
python3 watchdog.py
```
*Watchdog bot crash bo'lsa darhol restart qiladi va Telegramga xabar beradi.*

---

## 📱 BOT IMKONIYATLARI

1.  **📊 Texnik Tahlil:** SMC (FVG, Order Block, BOS) asosida real vaqtda tahlil.
2.  **🔔 Price Alerts:** Belgilangan narxga yetganda darhol xabar berish.
3.  **👨‍🏫 Jonli SMC Trener:** Multimodal AI mentor (Matn + Rasm + PDF + Word + Excel tahlili).
4.  **📈 P&L Hisoboti:** Oylik va haftalik foyda/zarar statistikasi.
5.  **📜 Signal Tarixi:** Oxirgi yuborilgan 10 ta signalni ko'rish.
6.  **📊 Tarixiy Audit:** `monthly_audit_backtest.py` orqali 1 oylik strategiya tahlili.
7.  **⚙️ Admin Panel:** Instrumentlarni qo'shish/o'chirish, risk va sifat filtrlarini sozlash.

---

## 🧪 TESTLARNI ISHGA TUSHIRISH

Har qanday yangilanishdan keyin testlarni yurgizish majburiydir:
```bash
# Barcha testlarni yurgizish
pytest tests/
```
*Xavfsizlik kamari: `test_signal_delivery.py` signal yetkazib berish zanjirini tekshiradi.*

---

**Loyiha holati:** `DEPLOY READY (10/10) - MASTER` ✅
