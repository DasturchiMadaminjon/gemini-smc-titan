# 🔱 Titan V27.2 Master Engine (2026 Edition)

Bu loyiha **SMC (Smart Money Concepts)** trading strategiyasi asosida qurilgan, 24/7 ishlovchi avtonom AI tizimidir. Loyihaning har bir qismi "Genetik Kod" tamoyillari asosida modullashtirilgan.

## 🧬 Genetik Kod Tamoyillari
1. **TDD (Test-Driven):** Barcha mantiq `tests/` papkasidagi testlar bilan 100% qoplangan.
2. **AI Native:** Gemini 2.5 Flash va Google Search integratsiyasi orqali real vaqtda internetdan ma'lumot tahlil qiladi.
3. **RAG (Knowledge):** `bilim_bazasi/` ichidagi barcha PDF va TXT fayllarni o'qib, shogirdlarga professional tushuntirish bera oladi.
4. **Self-Optimization (Genetic Engine):** Bot har 1 soatda o'z savdo tarixini tahlil qilib, SMC indikatorlarining sozlamalarini (`min_quality`, `tp_multiplier`) avtomatik tarzda optimallashtiradi.
5. **Watchdog:** AWS-da bot to'xtab qolmasligi uchun avtomatik restart va soatlik limit nazoratiga ega.
6. **Dynamic Quality Engine:** `min_quality` sozlamasi endi qat'iy emas, balki ballar yig'indisi (Trend, FVG, RR, Zone) asosida ishlaydi va bozordagi "shovqin"ni 5 baravargacha kamaytiradi.
7. **Enhanced Backtest:** 2026-yil 1-apreldan boshlab uzoq muddatli tahlil qilish va natijalarni Telegramga PDF/Xabar ko'rinishida yuborish imkoniyati qo'shildi.

## 📂 Loyiha Strukturasi (DNK Xaritasi)
- `bot.py`: Tizimning yuragi (Monitor Loop + AI Loop).
- `core/`: Matematik ko'z (SMC Indicator + Manager).
- `utils/ai_engine.py`: Tizimning miyasi (Gemini 2.5 + Google Search).
- `utils/rag_engine.py`: Tizimning xotirasi (Vector Search).
- `utils/telegram.py`: Tizimning ko'rinishi (Professional UI/UX).

## 🚀 Ishga tushirish va Buyruqlar

Loyihani turli muhitlarda (Windows, AWS, PythonAnywhere) boshqarish uchun barcha buyruqlar va test ko'rsatmalari alohida faylda jamlangan:

👉 **[COMMANDS.md](./COMMANDS.md)** — Barcha buyruqlar ro'yxati (Test, Start, Index).

### Tezkor boshlash (Lokal):
1. `.env` faylini to'ldiring.
2. `pip install -r requirements.txt` ni yurgizing.
3. `python bot.py` orqali ishga tushiring.

## 🛠 Xavfsizlik va Nazorat
- **Loglar:** `bot_log.txt` da barcha harakatlar (Signal yuborish, AI tahlili) muhrlanadi.
- **Restart:** `run.sh` bot o'chib qolsa, uni avtomatik qayta yoqadi.
- **Audit:** `tests/trader_audit.py` orqali tizimning strategik sog'lig'ini tekshirish mumkin.

---
*Ushbu loyiha 2026-yilning eng so'nggi AI yutuqlari asosida shakllantirilgan.*
