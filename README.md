# 🔱 Titan V27.2 Master Engine (2026 Edition)

Bu loyiha **SMC (Smart Money Concepts)** trading strategiyasi asosida qurilgan, 24/7 ishlovchi avtonom AI tizimidir. Loyihaning har bir qismi "Genetik Kod" tamoyillari asosida modullashtirilgan.

## 🧬 Genetik Kod Tamoyillari
1. **TDD (Test-Driven):** Barcha mantiq `tests/` papkasidagi testlar bilan 100% qoplangan.
2. **AI Native:** Gemini 2.5 Flash va Google Search integratsiyasi orqali real vaqtda internetdan ma'lumot tahlil qiladi.
3. **RAG (Knowledge):** `bilim_bazasi/` ichidagi barcha PDF va TXT fayllarni o'qib, shogirdlarga professional tushuntirish bera oladi.
4. **Watchdog:** AWS-da bot to'xtab qolmasligi uchun avtomatik restart va soatlik limit nazoratiga ega.

## 📂 Loyiha Strukturasi (DNK Xaritasi)
- `bot.py`: Tizimning yuragi (Monitor Loop + AI Loop).
- `core/`: Matematik ko'z (SMC Indicator + Manager).
- `utils/ai_engine.py`: Tizimning miyasi (Gemini 2.5 + Google Search).
- `utils/rag_engine.py`: Tizimning xotirasi (Vector Search).
- `utils/telegram.py`: Tizimning ko'rinishi (Professional UI/UX).

## 🚀 Ishga tushirish (AWS/Local)
1. `.env` fayliga `GEMINI_API_KEY` ni joylang.
2. Virtual muhitni sozlang: `python3 -m venv .venv && source .venv/bin/activate`
3. Kutubxonalarni o'rnating: `pip install -r requirements.txt`
4. Botni yoqing: `nohup ./run.sh > bot_log.txt 2>&1 &`

## 🛠 Xavfsizlik va Nazorat
- **Loglar:** `bot_log.txt` da barcha harakatlar (Signal yuborish, AI tahlili) muhrlanadi.
- **Restart:** `run.sh` bot o'chib qolsa, uni avtomatik qayta yoqadi.
- **Audit:** `tests/trader_audit.py` orqali tizimning strategik sog'lig'ini tekshirish mumkin.

---
*Ushbu loyiha 2026-yilning eng so'nggi AI yutuqlari asosida shakllantirilgan.*
