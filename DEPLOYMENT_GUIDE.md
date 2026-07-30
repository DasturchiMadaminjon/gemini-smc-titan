# 🚀 TITAN V27.2 A+ MASTER - DEPLOYMENT GUIDE (LINUX/AWS)

Ushbu qo'llanma botni AWS EC2 (Amazon Linux 2023) yoki har qanday Linux serverga professional darajada o'rnatish uchun mo'ljallangan.

---

## 1. SERVERNI TAYYORLASH

### Tizim paketlarini yangilash:
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git screen
```

### Loyihani yuklash:
```bash
git clone https://github.com/SIZNING_USER/REPO_NOMI.git
cd REPO_NOMI
```

---

## 2. VIRTUAL MUHIT (VENV) VA BOG'LIQLIKLAR

### Virtual muhit yaratish:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Kutubxonalarni o'rnatish:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. KONFIGURATSIYA (.env)

`.env` faylini yarating va API kalitlarni yozing:
```bash
nano .env
```
*Ichiga quyidagilarni yozing:*
```env
GEMINI_API_KEY=AIzaSyA...
TELEGRAM_BOT_TOKEN=867232...
```
*(Saqlash: Ctrl+O, Enter. Chiqish: Ctrl+X)*

---

---

## 4. BILIM BAZASINI INDEKSLASH (AI MENTOR)

Bot yangi kitoblar va ma'lumotlarni tanishi uchun ularni indekslash shart.

### Yangi fayllar qo'shish:
1. PDF yoki TXT fayllarni `bilim_bazasi/` papkasiga yuklang.
2. Quyidagi buyruqni bering:
```bash
python3 build_vectors.py
```
*Bu buyruq barcha fayllarni tahlil qilib, `vector_db/index.json` faylini yangilaydi.*

---

## 5. ISHGA TUSHIRISH (24/7 AUTONOMOUS)

Botni **Watchdog** bilan birga `screen` ichida ishga tushirish tavsiya etiladi. Bu serverdan chiqsangiz ham bot ishlashini ta'minlaydi.

### Yangi screen ochish:
```bash
chmod +x run.sh
./run.sh
```
*(Bu skript orqa fonda nohup yordamida watchdog ni va botni xavfsiz ishga tushiradi)*

---

## 5. MONITORING VA LOGLAR

Bot harakati va xatolarni real vaqtda ko'rish:
```bash
tail -f logs/bot.log
```

---

## 🛡️ XAVFSIZLIK QOIDALARI (GENETIC DNA)

1.  **Github:** Hech qachon `.env` yoki `data/*.db` fayllarini ochiq repozitoriyga yuklamang (`.gitignore` allaqachon sozlangan).
2.  **Backup:** Har haftada `data/trading_bot.db` faylini o'zingizga yuklab oling (Statistika yo'qolmasligi uchun).
3.  **Updates:** Kodni yangilagandan so'ng har doim `pytest tests/` buyrug'ini bering.

---
**Loyiha holati:** `DEPLOY READY` ✅
