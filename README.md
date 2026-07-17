# Titan V27.2 SMC Trading Bot

Titan V27.2 - bu Smart Money Concepts (SMC) asosida ishlaydigan, **Gemini yoki Claude AI** bilan tasdiqlanadigan avtonom trading bot.

## Xususiyatlari
- **Professional SMC Tahlil**: BOS, OrderBlock, FVG va Liquidity.
- **Dual AI Provayder**: Gemini Flash yoki Claude Sonnet — tugma orqali almashish mumkin. (Sprint 14)
- **AI Fail-Safe Fallback**: Claude xatoga uchrasa Gemini avtomatik ishga tushadi.
- **Resilient Messaging**: "Smart Chunking" va "HTML Sanitization".
- **AI Self-Healing**: Chala qolgan AI tahlillarini avtomatik qayta tiklash.
- **24/7 Avtonomiya**: AWS EC2 uchun optimallashtirilgan Watchdog tizimi.
- **TDD Safety**: 100% testlardan o'tgan barqaror kod bazasi.
- **A'zolar Boshqaruvi**: PUBLIC/RESTRICTED rejimlar, bloklash va whitelist.

## 🚀 O'rnatish (AWS EC2)

1. **Repozitoriyani yuklash**:
   ```bash
   git clone https://github.com/DasturchiMadaminjon/gemini-smc-titan.git
   cd gemini-smc-titan
   ```

2. **Kutubxonalarni o'rnatish**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Konfiguratsiya**:
   `.env` faylini yarating va API kalitlarni kiriting:
   ```env
   TELEGRAM_BOT_TOKEN=...
   GEMINI_API_KEYS=key1,key2,key3
   # Ixtiyoriy: Claude kaliti (yo'q bo'lsa ham bot ishlaydi)
   CLAUDE_API_KEY=sk-ant-...
   ```
   Claude tanlash uchun Telegram da: `Sozlamalar` → `AI: 🟢 GEMINI` tugmasini bosing.

4. **Ishga tushirish**:
   ```bash
   nohup python3 watchdog.py > logs/watchdog.log 2>&1 &
   ```

## 🧪 Testlarni yurgizish
Tizim barqarorligini tekshirish uchun:
```bash
python3 -m pytest tests/
```

## 📜 Litsenziya
Loyiha faqat o'quv va shaxsiy foydalanish uchun mo'ljallangan. Savdoda ehtiyot bo'ling!
