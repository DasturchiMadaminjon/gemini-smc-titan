# Titan V27.2 SMC Architecture 🚀

Titan V27.2 — bu Smart Money Concepts (SMC) tamoyillariga asoslangan, AI tomonidan tasdiqlanadigan professional savdo tizimi.

## 🏗 Tizim Tarkibi

### 1. Market Data Layer (yfinance)
AWS EC2 IP-blokirovkalari sababli, tizim **yfinance** backend-ga o'tkazilgan. 
- **Retries**: Ma'lumot olishda 3 marta qayta urinish (exponential backoff) mantiqi qo'shilgan.
- **Accuracy**: XAU/USD (Gold) va boshqa instrumentlar tickerlarining mantiqiy diapazoni TDD orqali nazorat qilinadi.

### 2. SMC Indicator Engine (`core/indicator.py`)
- **SMC Setup**: BOS, CHoCH, OrderBlocks va Liquidity zonalarini aniqlaydi.
- **Visualization**: `mplfinance` yordamida professional grafiklar yaratadi. `numpy.float64` tiplari bilan ishlashda 100% xavfsiz (Standard Python floats cast).

### 3. AI Validation Layer (`utils/ai_engine.py`)
- **Model**: Gemini 2.5 Flash (Vision + RAG).
- **Security (Auto-Rotation)**: Agar bitta API kalit bloklansa (403 Leaked), tizim avtomatik ravishayda backup kalitlarga o'tadi.
- **Token Optimization**: Xabarlar kesilib qolmasligi uchun `max_output_tokens=2048` qilib sozlangan.

### 4. Safety & TDD Layer (`tests/`)
Loyiha **TDD (Test-Driven Development)** asosida barqarorlashtirilgan:
- `test_collection_safety_tdd.py`: Kolleksiyalar (set vs list) bilan ishlashda fatal errorlarni oldini oladi.
- `test_visualization_safety_tdd.py`: Grafik chizishda biblioteka mosligini tekshiradi.
- `test_exchange_stability_tdd.py`: Ma'lumot provayderi ishonchliligini tasdiqlaydi.
- `test_ai_key_rotation_tdd.py`: AI kalitlarining blokirovkalarga chidamliligini isbotlaydi.

## 🛠 Deployment (AWS EC2)

1. **Watchdog**: `watchdog.py` botni 24/7 nazorat qiladi va xatolik bo'lsa darhol qayta ishga tushiradi.
2. **Logs**: `logs/watchdog.log` va `logs/bot.log` orqali real vaqtda monitoring qilinadi.

---
*Titan V27.2 - Barqarorlik va Professionalizm uchun yaratilgan.*
