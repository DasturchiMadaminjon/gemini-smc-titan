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

## 🧪 Tahlil To'g'riligini Tekshirish (TDD)
Botning matematik va texnik tahlili to'g'ri ishlayotganini aniqlash va nazorat qilish uchun quyidagi maxsus TDD test to'plamlari mavjud:

1. **Matematik va SMC Strukturaviy Tahlil Testlari (`tests/test_indicator_quant.py`):**
   * **Swing nuqtalarini aniqlash** (`_get_swings`) — pivotlarni to'g'ri hisoblaydi.
   * **EMA 200 trend guard** (`_get_trend`) — HTF trendni xatosiz aniqlaydi.
   * **Fibonacci Premium/Discount zonalari** (`_get_fibo_zone`) — narx savdoga mos zonada ekanini tekshiradi.
   * **BOS va Sweep farqlash** (`_detect_structure_break`) — tana bilan yopilish (BOS) va shunchaki soya bilan likvidlik yig'ish (Sweep) hodisalarini adashtirmasdan farqlaydi.
   * **FVG (Fair Value Gap) detection** (`_find_unmitigated_fvg`) — bozor bo'shliqlarini aniqlaydi.
   * **R:R validation filter** — risk-mukofot nisbati 1:1.5 dan past signallarni filtrlaydi.
2. **AI Vizual va Kontekst Tahlili Testlari (`tests/test_ai_visual_evaluation_tdd.py`):**
   * Gemini AI grafik rasmini va narxlarni SMC qoidalari bo'yicha to'g'ri o'qib, `TASDIQLAYMAN` yoki `RAD ETAMAN` qarorini to'g'ri bera olishini tekshiradi.
3. **Simbolni Matndan Dinamik Aniqlash Testlari (`tests/test_chat_symbol_detection.py`):**
   * Foydalanuvchi umumiy chatda "gold", "oltin", "btc", "XAU/USD" deb yozganda bot buni dinamik aniqlab, AI tahliliga real-time chart va narx ma'lumotlarini to'liq joylashini kafolatlaydi.

* **Barcha tahlil testlarini yurgizish buyrug'i:**
  ```bash
  python3 -m pytest tests/test_indicator_quant.py tests/test_ai_visual_evaluation_tdd.py tests/test_chat_symbol_detection.py -v
  ```

---

## 🚀 AWS Linux Serverda Yangilash va Qayta Ishga Tushirish

Koddagi barcha o'zgarishlar GitHub'ga muvaffaqiyatli jo'natildi. Uni AWS serveringizda yangilash, TDD sinovidan o'tkazish va 24/7 rejimda qayta ishga tushirish uchun quyidagi amallarni bajaring:

### 1. GitHub'dan Eng So'nggi Kodni Yuklash:
Serveringizga kiring va loyiha papkasiga o'tib, yangilanishlarni tortib oling:
```bash
cd ~/temp_master_zip
git pull origin main
```

### 2. TDD Testlarini Yurgizib Tahlil To'g'riligini Tasdiqlash:
Virtual muhitni faollashtiring va testlarni ishga tushiring:
```bash
source venv/bin/activate
python3 -m pytest tests/test_indicator_quant.py tests/test_ai_visual_evaluation_tdd.py tests/test_chat_symbol_detection.py -v
```
*(Barcha testlar "PASSED" bo'lishi shart).*

### 3. Botni 24/7 Rejimida Qayta Ishga Tushirish (Screen orqali):
Eski ishlayotgan bot jarayonlarini butunlay to'xtatib, screen ichida Watchdog orqali botni qayta yoqing:
```bash
# 1. Eski bot va watchdog jarayonlarini butunlay to'xtatish
pkill -f watchdog.py
pkill -f bot.py

# 2. Yangi fondagi screen sessionda botni ishga tushirish
screen -S titan_bot -d -m bash -c "source venv/bin/activate && python3 watchdog.py"
```

### 4. Real-Time Skanerlash Loglarini Kuzatish:
Bot bozorlarni qanday skanerlayotgani va foydalanuvchilar bilan muloqotini ko'rish uchun loglarni kuzating:
```bash
# Skaner va xabarlar logini kuzatish
tail -f bot_log.txt

# Yoki batafsil tizimli loglarni ko'rish
tail -f logs/bot.log
```

---

## ⚠️ Diqqat qiling
- Barcha statistika va kutilayotgan bitimlar (Pending Signals) bot o'chib-yonganida ham o'chib ketmaydi (ular `titan.db` ichida turadi).
- Agar AI limiti (429 Rate Limit) tugasa, bot avtomatik ravishda "Draft Mode" (shablon javoblar) rejimiga o'tadi va jarayon to'xtab qolmaydi.
