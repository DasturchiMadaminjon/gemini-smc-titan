# 📖 GEMINI TITAN V27.2 A+ MASTER — Foydalanish Yo'riqnomasi

Ushbu qo'llanma botning asosiy funksiyalaridan qanday samarali foydalanishni tushuntiradi. Barcha ma'lumotlar xavfsiz tarzda SQLite bazasida (data/titan.db) saqlanadi.

---

## 🛠 Telegram Buyruqlari

### 1. Asosiy Menyular
- **📊 Texnik Tahlil**: Tanlangan instrument bo'yicha darhol SMC tahlili va chart rasmini generatsiya qiladi.
- **🌐 Fundamental**: Global iqtisodiy drayverlar (DXY, FED, NFP) bo'yicha AI xulosasini beradi.
- **👨‍🏫 Jonli SMC Trener**: AI bilan muloqot qilish, chartlarni tahlil qildirish va darslar olish.
- **💬 AI Chat Assistant**: Kengaytirilgan AI yordamchisi (xotiraga ega).
- **⚡ Scalping AI**: Tezkor bozor harakatlari (M5, M15) uchun scalping strategiyalari.
- **📈 Hisobot (Analytics)**: Oxirgi 50 ta bitimning Win-rate va R:R statistikasini AI ko'zi bilan chuqur tahlil qiladi (Survival Bias ni hisobga olgan holda).
- **📖 Qo'llanma**: Ushbu menyular bo'yicha yordam.

### 2. Admin Buyruqlari (Maxsus Ruxsat)
- **⚙️ Sifat**: 
    - `🟢 30%`: Yumshoq rejim (ko'p signal, ko'p risk).
    - `🟡 50%`: O'rta rejim.
    - `🟠 75%`: Tavsiya etilgan (optimal) rejim.
    - `🔴 90%`: Faqat eng kuchli signallar.
- **⚖️ Risk Status**: Botning joriy "Sog'lig'i"ni (Balans va Loss Streak) ko'rsatadi.
- **🧪 Test Signal**: Qo'lda sun'iy signal kiritib, tizimni va analitikani sinovdan o'tkazish.
- **🔍 Backtest (Apr-May)**: `python3 backtest_100_signals.py` buyrug'i orqali aprel oyidan beri bo'lgan tarixni tahlil qilish va natijani Telegramga olish.
- **🚨 PANIC CLOSE ALL**: Barcha ochiq savdolarni shoshilinch yopish va bot ishini vaqtincha to'xtatish.

---

## 3. Webhook (TradingView) Integratsiyasi
Agar siz TradingView orqali botga signal olmoqchi bo'lsangiz:
1. Pine Scriptingizga `alert()` funksiyasini qo'shing.
2. Webhook URL qilib serveringizni (PythonAnywhere) kiriting: `https://<sizning_domen>.pythonanywhere.com/webhook`
3. Signal JSON formatda bo'lishi kerak: `{"symbol": "EUR/USD", "direction": "buy", "entry": 1.10, "sl": 1.09, "tp": 1.12}`
4. Kelgan har bir Webhook signal "AI Xulosa" (Kill Zone va R:R hisobi) tekshiruvidan o'tadi.

---

## 🧪 Testlash Muhiti (TDD)
Tizim barqarorligini tasdiqlash uchun:
- **Barcha testlarni yurgizish**: `pytest tests/` (136 ta testdan iborat TDD muhiti)
- **Signal qabul qilinishini tekshirish**: "🧪 Test Signal" tugmasini bosib tekshiring.

---

## ⚠️ Diqqat qiling
- Barcha statistika va kutilayotgan bitimlar (Pending Signals) bot o'chib-yonganida ham o'chib ketmaydi (ular `titan.db` ichida turadi).
- Agar AI limiti (429 Rate Limit) tugasa, bot avtomatik ravishda "Draft Mode" (shablon javoblar) rejimiga o'tadi va jarayon to'xtab qolmaydi.
