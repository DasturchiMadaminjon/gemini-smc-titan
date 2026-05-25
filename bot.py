import os, asyncio, threading, logging, yaml, warnings, json, sys, time

# ✅ CCXT Marshmallow xatosini to'g'irlash (Windows Bug Fix)
try:
    import marshmallow
    sys.modules['ccxt.marshmallow'] = marshmallow
except ImportError:
    pass

from datetime import datetime, timezone, timedelta
from core.genetic_optimizer import GeneticStrategyOptimizer
from dotenv import load_dotenv
from utils.persistence import load_state, save_state, load_extras, save_extras
from utils.exchange import ExchangeClient
from utils.telegram import TelegramNotifier
from utils.chart_generator import generate_chart_buffer
from utils.database import DatabaseManager       # ✅ #2,4: DB integratsiya
from core.watcher import MarketWatcher           # ✅ #3: MTF Guard
from core.manager import TradeManager
from utils.news import NewsWatcher
from utils.rag_engine import RAGEngine
from utils.web_search import web_search

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiBot:
    def __init__(self):
        with open('config/settings.yaml', 'r') as f: self.cfg = yaml.safe_load(f)
        
        # API kalitlarini yig'ish ( .env VA config dan)
        load_dotenv()
        env_keys = os.getenv('GEMINI_API_KEY', '')
        
        # settings.yaml dagi kalitlarni ham o'qish (agar bo'lsa)
        self.api_keys = []
        raw_keys = self.cfg.get('gemini_ai', {}).get('api_keys', [])
        if isinstance(raw_keys, list): self.api_keys.extend(raw_keys)
        
        # .env dagi kalitlarni qo'shish (vergul bilan ajratilgan)
        if env_keys:
            self.api_keys.extend([k.strip() for k in env_keys.split(',') if len(k.strip()) > 20])
        
        self.api_keys = list(set(self.api_keys)) # Dublikatlarni olib tashlash
        
        # MUHIM: Kalitlarni config ichiga joylaymiz, chunki TelegramNotifier undan o'qiydi
        if 'gemini_ai' not in self.cfg: self.cfg['gemini_ai'] = {}
        self.cfg['gemini_ai']['api_keys'] = self.api_keys
        
        print(f"[AUTH] Gemini API kalitlari yuklandi: {len(self.api_keys)} ta")
        if len(self.api_keys) == 0:
            print("[WARNING] Hech qanday API kalit topilmadi! .env faylini tekshiring.")
        
        self.bot_token = self.cfg.get('telegram', {}).get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.cfg['telegram']['bot_token'] = self.bot_token
        
        # Xotirani yuklash (Memory Persistence)
        saved = load_state()
        self.bot_state = saved if saved else {
            'symbols': {},
            'terminal': {'balance': 5000.0}, 'ai_requests': [], 'loss_streak': 0
        }
        
        # Yangi simvollarni xotiraga qo'shish (Sinxronizatsiya)
        for s in self.cfg['symbols']:
            if s not in self.bot_state['symbols']:
                self.bot_state['symbols'][s] = {'price': 0.0}

        # Restart da eski navbatni tozalash (dublikat xabarlar oldini olish)
        self.bot_state['ai_requests'] = []
        save_state(self.bot_state)

        self.lock = threading.Lock()
        print("INFO: Telegram modulli yuklanmoqda...")
        self.telegram = TelegramNotifier(self.cfg, self.lock)
        print("OK: Telegram tayyor.")

        print("INFO: Birja (Exchange) yuklanmoqda...")
        self.exchange = ExchangeClient(self.cfg)
        print("OK: Birja tayyor.")

        print("INFO: Ma'lumotlar bazasi yuklanmoqda...")
        self.db = DatabaseManager()
        print("OK: Baza tayyor.")

        print("INFO: Market Watcher yuklanmoqda...")
        self.watcher = MarketWatcher(self.cfg, self.exchange)
        print("OK: Watcher tayyor.")

        print("INFO: News Watcher yuklanmoqda...")
        self.news = NewsWatcher(self.cfg)
        print("OK: News tayyor.")

        print("INFO: Trade Manager yuklanmoqda...")
        self.trades = TradeManager(self.cfg, self.db, self.telegram)
        
        # 🧬 Genetik Kod: Ongli rivojlanish moduli
        self.optimizer = GeneticStrategyOptimizer(population_size=10)
        self.last_evolution = datetime.now()
        
        self.trades.loss_streak = self.bot_state.get('loss_streak', 0)
        print("OK: Trade Manager tayyor.")

        # ✅ Deploy tayyorligi: Restart'dan omon qaladigan extras yuklash
        extras = load_extras()
        self.telegram.price_alerts   = extras['price_alerts']
        self.telegram.onboarding_done = extras['onboarding_done']
        # dedup_cache ni manager ga ham qaytarish (str key, restart'dan keyin saqlanadi)
        for h, ts_str in extras['dedup_cache'].items():
            try:
                self.trades._sent_signals[h] = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
            except Exception:
                pass
        # 📚 Bilim Bazasi va RAG ulanishi
        self.rag = RAGEngine(api_keys=self.api_keys)
        self.telegram.ai.rag = self.rag
        self.kb_files = self._get_kb_files()
        
        print(f"[EXTRAS] Yuklandi: {len(self.telegram.price_alerts)} alert user, "
              f"{len(self.trades._sent_signals)} dedup entry")


    def _get_kb_files(self):
        """bilim_bazasi papkasidagi fayllar ro'yxatini olish"""
        kb_path = 'bilim_bazasi'
        if not os.path.exists(kb_path):
            os.makedirs(kb_path)
            return []
        return [f for f in os.listdir(kb_path) if os.path.isfile(os.path.join(kb_path, f))]


    async def _handle_ai(self, req):
        uid = req['chat_id']; s = req['symbol']; t = req['type']
        p = self.bot_state['symbols'].get(s, {}).get('price', 0)
        
        # Narx 0 yoki yo'q bo'lsa — real vaqtda yfinance orqali olish (fundamental, chat uchun)
        if p == 0 and s not in ('SMC', 'ALL', 'DXY', 'NASDAQ', 'S&P500'):
            try:
                from utils.price_fetcher import get_current_price
                import asyncio as _asyncio
                price_str = await _asyncio.get_event_loop().run_in_executor(None, get_current_price, s)
                # "Hozirgi vaqtda XAU/USD narxi: 2340.50 USD." dan raqamni ajratib olamiz
                import re as _re
                nums = _re.findall(r'[\d,]+\.?\d*', price_str.replace(',', ''))
                if nums:
                    p = float(nums[0])
            except Exception as _pe:
                logger.warning(f"Price fetch fallback error ({s}): {_pe}")
        img = req.get('image')
        
        # Avtomatik Chart generatsiyasi va Kontekst yig'ish
        if t in ['technical', 'scalping', 'chat', 'mentor_qa', 'fundamental', 'mentor_lessons', 'mentor_live_examples'] and s not in ('SMC', 'ALL'):
            try:
                df = await self.exchange.fetch_ohlcv(s, '1h', limit=100) # Oxirgi 100 soat (4 kun)
                if df is not None and not df.empty:
                    if not img and t in ['technical', 'scalping']:
                        img = await generate_chart_buffer(df)
                    # AI tahlili uchun narxlarni ham matn ko'rinishida qo'shamiz
                    ohlc_text = df.tail(48).to_string()
                    print(f"[DEBUG] {s} uchun OHLC jadvali AI promptiga muvaffaqiyatli qo'shildi ({len(ohlc_text)} bayt)")
                    req['text'] = f"{req.get('text', '')}\n\n[SISTEMA MA'LUMOTI: Hozirgi sana va vaqt: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Foydalanuvchi taqdim etgan signal natijasini aniqlashingiz uchun, men sizga {s} ning oxirgi 48 soatlik haqiqiy narxlarini (OHLC 1H) taqdim etaman. Ushu ma'lumotlarga qarab xulosa qiling. 'Menda narxlar yo'q' yoki 'kelajakni bilmayman' deb aytishingiz qat'iyan taqiqlanadi, chunki narxlar mana shu yerda keltirilgan!]\n\nNARXLAR JADVALI (OHLC):\n{ohlc_text}"
            except Exception as e:
                logger.error(f"DEBUG: Avto-chart xatosi: {e}")

        await self.telegram.send_action(uid, "upload_photo" if img else "typing")

        news_context = ""
        web_context = ""

        if t == 'analytics':
            from utils.analytics import generate_trade_report
            with self.lock:
                report_data = generate_trade_report(self.bot_state)
            prompt_text = report_data
        else:
            # ✅ Fundamental tahlil uchun real yangiliklar kontekstini yig'ish
            if t == 'fundamental':
                try:
                    # news_watcher dan oxirgi yangiliklarni olish
                    upcoming = await self.news.check_upcoming_news()
                    if upcoming:
                        news_context = "\nYAQIN ORADAGI YANGILIKLAR (REAL-TIME):\n" + "\n".join([f"- {n['event']} ({n['country']}) - {n['date']}" for n in upcoming])
                except Exception as e:
                    logger.warning(f"AI news context error: {e}")

        # 🌐 INTERNET QIDIRUVI — Chat, Fundamental va Mentor uchun real vaqt konteksti
        if t in ['chat', 'fundamental', 'mentor_lessons', 'mentor_qa', 'mentor_live_examples']:
            try:
                # Qidiruv so'rovini tuzish
                if t == 'fundamental':
                    search_q = f"{s} fundamental analysis forex news 2026"
                elif t == 'chat':
                    user_text_q = req.get('text', '')
                    search_q = user_text_q[:100] if user_text_q else f"{s} market news"
                else:  # mentor
                    search_q = req.get('text', '')[:100] or "SMC Smart Money Concepts trading 2026"
                
                loop = asyncio.get_event_loop()
                web_context = await loop.run_in_executor(None, web_search, search_q, 3)
                if web_context:
                    print(f"[WEB] '{search_q[:60]}' uchun internet natijasi olindi.")
            except Exception as ws_err:
                print(f"[WEB] Qidiruv xatosi: {ws_err}")

        prompts = {
            'analytics':   f"{prompt_text if t=='analytics' else ''}",
            'technical':   f"Instrument: {s} | Joriy narx: {p}\n{req.get('text', '')}\nMana oxirgi 100 ta sham charti. SMC metodikasi asosida TO'LIQ texnik tahlil ber. Grafikdagi zonalarni va OHLC ma'lumotlarini izohla.",
            'scalping':    f"Instrument: {s} | Joriy narx: {p}\n{req.get('text', '')}\nMana oxirgi 100 ta sham charti. M5/M15 uchun tezkor scalping kirish rejasini ber.",
            'fundamental': f"Instrument: {s} | Joriy narx: {p}{news_context}\n{web_context}\nFAQAT makro drayverlar (DXY, FED, yangiliklar) asosida fundamental tahlil qil. SMC aytma. Hozirgi sana {datetime.now().strftime('%Y-%m-%d %H:%M')}, ma'lumotlar real vaqtdagidir.",
            'chat':        f"[SISTEMA: Hozirgi vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}].\nDIQQAT: Matn oxirida berilgan OHLC narxlar jadvalidan to'liq foydalaning va signal qanday yakun topganini hisoblab bering.\n\n" + (f"{web_context}\n\n" if web_context else "") + f"{req.get('text', '')}" + (" [Rasm yuborildi — SMC tahlil qil. BOS, CHoCH, OB va FVG darajalarini qidir. Kirish va risk-menejment bo'yicha maslahat ber.]" if img else ""),
            'mentor_lessons':       f"[SISTEMA: Hozirgi vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}].\n" + (f"{web_context}\n\n" if web_context else "") + f"{req.get('text', '')}",
            'mentor_qa':            f"[SISTEMA: Hozirgi vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}].\nDIQQAT: Matn oxirida berilgan OHLC narxlar jadvalidan foydalanib xulosa qiling.\n\n" + (f"{web_context}\n\n" if web_context else "") + f"{req.get('text', '')}" + (" [Rasm yuborilgan bo'lsa SMC tahlil qil]" if img else ""),
            'mentor_live_examples': f"[SISTEMA: Hozirgi vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}].\n" + (f"{web_context}\n\n" if web_context else "") + f"{req.get('text', '')}"
        }
        prompt = prompts.get(t, prompts['technical'])

        # Exponential Backoff: 503/429 bo'lsa 3 marta qayta urinish
        max_retries = 3
        res = "" # Bo'sh qoldiramiz
        
        for attempt in range(max_retries):
            try:
                # Debug log: Bog'liqlikni tekshirish uchun
                logger.info(f"[AI-DEBUG] Request for {s}: context={t}, image_present={img is not None}, data_len={len(req.get('text',''))}")
                
                res = await self.telegram.get_ai_analysis(prompt, uid, context=t, image_data=img)
                
                # Agar AI javobi xato haqida bo'lsa (leaked key kabi), qayta urinib o'tirmaymiz
                if "❌ XATO" in res or "❌ API" in res:
                    break 

                # Agar AI Draft qaytarsa va bu oxirgi urinish bo'lmasa, qayta urinishni chaqiramiz
                if "DRAFT" in res and attempt < max_retries - 1:
                    raise Exception("429 API Band (Draft qaytdi)")
                    
                break  # Muvaffaqiyatli — to'xtaymiz
            except Exception as e:
                err = str(e)
                if "503" in err or "429" in err:
                    wait = (attempt + 1) * 3
                    logger.warning(f"AI Busy. Attempt {attempt+1}/{max_retries}. Wait {wait}s...")
                    await asyncio.sleep(wait)
                    res = f"⚠️ Server hozircha band (Attempts: {attempt+1})"
                else:
                    res = f"❌ AI Tizim Xatoligi: {err[:150]}"
                    break
        
        if not res:
            res = "⚠️ AI tizimiga ulanib bo'lmadi. Kalitlarni tekshiring."
        elif "429" in str(res) or "Rate limit" in str(res):
            # Sprint 2 #2: 429 limitini treyderni xabardor qilish
            res = "⚠️ <b>Gemini API limit to'lib qoldi!</b>\n\n1-2 daqiqada qayta yuboring.\n<i>Sabab: Bir vaqtda ko'p so'rov yuborildi.</i>"

        # ✅ #4: AI chat tarixini DB ga saqlash
        if t == 'chat':
            user_msg = req.get('text', '')
            if user_msg:
                self.db.add_chat_message(uid, 'user', user_msg)

        # ✅ Xatolik oldini olish: HTML parser xatosi (Telegram) bermasligi uchun
        if res and '❌' not in res:
            # Telegram HTML qoidalari: &, <, > belgilari escape qilinishi shart
            res = res.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        await self.telegram.send(f"🤖 <b>AI {t.upper()} TAHLILI ({s}):</b>\n\n{res}", cid=uid)

        # ✅ #4: AI javobini ham DB ga saqlash
        if t == 'chat' and res and '❌' not in res:
            self.db.add_chat_message(uid, 'assistant', res[:500])

    async def _ai_loop(self):
        """AI so'rovlarini qayta ishlash loopi"""
        MAX_QUEUE = 50  # Sprint 2 #3: Memory leak himoyasi
        while True:
            reqs = []
            with self.lock:
                if self.bot_state.get('ai_requests'):
                    # Eski so'rovlarni tozalash (MAX_QUEUE dan oshsa)
                    if len(self.bot_state['ai_requests']) > MAX_QUEUE:
                        dropped = len(self.bot_state['ai_requests']) - MAX_QUEUE
                        self.bot_state['ai_requests'] = self.bot_state['ai_requests'][-MAX_QUEUE:]
                        logger.warning(f"[MEMORY] ai_requests tozalandi: {dropped} ta eski so'rov o'chirildi")
                    reqs = self.bot_state['ai_requests']
                    self.bot_state['ai_requests'] = []
            
            for i, r in enumerate(reqs):
                try: await self._handle_ai(r)
                except Exception as e: logger.error(f"AI Handle error: {e}")
                # Ketma-ket so'rovlar orasida 3 soniya kutish (Rate limit oldini olish)
                if i < len(reqs) - 1:
                    await asyncio.sleep(3)
            
            await asyncio.sleep(2)
    async def _process_pending_signals(self, symbol, df):
        """Ochiq qolgan signallarni jonli tahlil qilish (Timeout va Breakeven)"""
        pending = self.db.get_pending_signals()
        # p = (id, symbol, direction, entry, sl, tp1, timestamp)
        now = datetime.now(timezone.utc)
        curr_p = float(df['close'].iloc[-1])
        
        for p in pending:
            p_id, p_sym, p_dir, p_entry, p_sl, p_tp1, p_time_str = p
            if p_sym != symbol:
                continue
                
            try:
                # SQLite timestamp ni datetime ga o'girish (u UTC da saqlanadi odatda, yoki naive local)
                try:
                    p_time = datetime.strptime(p_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                except ValueError:
                    try:
                        p_time = datetime.strptime(p_time_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
                    except ValueError:
                        # Fallback parsing
                        p_time = datetime.fromisoformat(p_time_str).replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"Baza vaqti parsing xatosi (signal {p_id}): {e}")
                continue

            elapsed_hours = (now - p_time).total_seconds() / 3600
            
            # 1. Breakeven & Win Check (Juda soddalashtirilgan jonli check)
            # Aslida CCXT orqali oxirgi N sham high/low qaralishi kerak, lekin jonli ishlayotganda hozirgi narx yetarli
            if p_sl is None or p_tp1 is None:
                self.db.update_signal_result(p_id, 'IGNORED (OLD)')
                continue

            is_win = False
            is_loss = False
            if p_dir == 'BUY':
                if curr_p >= p_tp1: is_win = True
                elif curr_p <= p_sl: is_loss = True
            else:
                if curr_p <= p_tp1: is_win = True
                elif curr_p >= p_sl: is_loss = True

            if is_win:
                msg = f"✅ <b>TARGET REACHED!</b>\n\n🎯 {p_sym} signali TP1 ga yetib keldi.\n👉 <i>Maslahat: SL ni kirish narxiga (Zararsizlikka) ko'chiring yoki qisman yoping!</i>"
                await self.telegram.send(msg)
                self.db.update_signal_result(p_id, 'WIN')
                continue
            elif is_loss:
                # Agar SL urilgan bo'lsa, xabar jo'natmasak ham mayli, asabiylashmasligi uchun. Yoki yuboramiz.
                self.db.update_signal_result(p_id, 'LOSS')
                continue

            # 2. Timeout (12 soatdan oshsa)
            if elapsed_hours >= 12.0:
                pnl = curr_p - p_entry if p_dir == 'BUY' else p_entry - curr_p
                pnl_perc = (pnl / p_entry) * 100 if p_entry else 0.0
                quote_currency = p_sym.split('/')[-1] if '/' in p_sym else 'USDT'
                if pnl > 0:
                    status_text = f"+{pnl_perc:.2f}% (+{pnl:.4f} {quote_currency} Narx Farqi) (Plyusda)"
                elif pnl < 0:
                    status_text = f"-{abs(pnl_perc):.2f}% (-{abs(pnl):.4f} {quote_currency} Narx Farqi) (Minusda)"
                else:
                    status_text = f"0.00% (0.0000 {quote_currency} Narx Farqi) (Fletda)"
                
                msg = (
                    f"⏳ <b>TIMEOUT ALERT (12 soat)</b>\n\n"
                    f"⚠️ {p_sym} signali uzoq vaqt fletda (Range) qolib ketdi.\n"
                    f"📊 Hozirgi holat: {status_text}\n\n"
                    f"💡 <i>Prop-Trading qoidalari asosida kapitalni (marginni) himoya qilish uchun pozitsiyani hozirgi narxda yopishingiz tavsiya qilinadi!</i>"
                )
                await self.telegram.send(msg)
                self.db.update_signal_result(p_id, 'TIMEOUT')

    async def _market_loop(self):
        # Startup Message
        now_utc = datetime.now(timezone.utc)
        now_uzb = now_utc + timedelta(hours=5)
        
        start_msg = (
            "🚀 <b>GEMINI SMC TITAN V27 — Ishga tushdi</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Instrumentlar: {', '.join(self.cfg['symbols'])}\n"
            f"⏱️ Timeframe: {self.cfg.get('timeframe', '15m')}\n"
            f"🕐 Vaqt (UTC): {now_utc.strftime('%d.%m.%Y %H:%M')}\n"
            f"🇺🇿 Vaqt (UZB): {now_uzb.strftime('%d.%m.%Y %H:%M')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Signal kutilmoqda..."
        )
        
        # Klaviaturani startup xabari bilan yuborish
        main_kb = {'keyboard': [
            [{'text': "\U0001F4CA Texnik Tahlil"}, {'text': "\U0001F310 Fundamental"}],
            [{'text': "\U0001F468\u200D\U0001F3EB Jonli SMC Trener"}, {'text': "\U0001F4AC AI Chat Assistant"}],
            [{'text': "\u26A1 Scalping AI"}, {'text': "\U0001F4C8 Hisobot (Analytics)"}],
            [{'text': "\u2699\uFE0F Sozlamalar"}, {'text': "\u2696\uFE0F Risk Status"}],
            [{'text': "\U0001F4D6 Qo'llanma"}, {'text': "\U0001F9EA Test Signal"}],
            [{'text': "\U0001F6A8 PANIC CLOSE ALL"}]
        ], 'resize_keyboard': True}
        
        # ✅ Watchdog uchun darhol heartbeat yozish
        try:
            with open('data/heartbeat.txt', 'w') as f: f.write(str(time.time()))
        except: pass

        await self.telegram.send(start_msg, kb=json.dumps(main_kb))
        
        print("Titan V27.2 A+ MASTER ENGINE IS LIVE!")
        
        while True:
            # ✅ Panic Mode Check (Sprint 4)
            if self.bot_state.get('panic_request'):
                await asyncio.sleep(10)
                continue
            # ✅ #1: Telegramdan o'zgargan sozlamalarni har bir siklda qayta yuklash
            try:
                with open('config/settings.yaml', 'r') as f:
                    new_cfg = yaml.safe_load(f)
                    if new_cfg:
                        self.cfg = new_cfg
                        # Skaner va savdo menejerini ham yangilash
                        self.watcher.cfg = new_cfg
                        self.trades.cfg = new_cfg
                        
                        # ✅ Xotirani (bot_state) yangi simvollar bilan sinxronlash
                        with self.lock:
                            for s in self.cfg['symbols']:
                                if s not in self.bot_state['symbols']:
                                    self.bot_state['symbols'][s] = {'price': 0.0}
            except Exception as e:
                print(f"DEBUG: Sozlamalarni yangilashda xato: {e}")

            # ✅ Yangiliklarni tekshirish (High Impact)
            try:
                upcoming_news = await self.news.check_upcoming_news()
                for news in upcoming_news:
                    news_msg = (
                        f"🚨 <b>MUHIM IQTISODIY YANGILIK!</b>\n\n"
                        f"🌍 Davlat: {news.get('country')}\n"
                        f"📢 Hodisa: {news.get('event')}\n"
                        f"⚠️ Daraja: High Impact\n"
                        f"⏰ Vaqt: {news.get('date')}\n\n"
                        f"ℹ️ <i>Eslatma: Kuchli yangiliklar vaqtida savdodan ehtiyot bo'ling!</i>"
                    )
                    await self.telegram.send(news_msg)
            except Exception as e:
                print(f"DEBUG: News check error: {e}")

            for s in self.cfg['symbols']:
                print(f"[SCANNER] {s} tekshirilmoqda...")
                sig = None
                df = await self.exchange.fetch_ohlcv(s, self.cfg.get('timeframe', '15m'), limit=200)
                if df is not None and not df.empty:
                    curr_p = float(df['close'].iloc[-1])
                    
                    # ✅ LIVE PENDING CHECK (Breakeven & Timeout)
                    await self._process_pending_signals(s, df)

                    # ✅ #3: MTF HTF trend ni kesh orqali olish
                    htf_trend = self.watcher.get_cached_trend(s)
                    if htf_trend is None:
                        try:
                            htf_trend = await self.watcher.get_htf_trend(s)
                            if htf_trend:
                                self.watcher.update_mtf_cache(s, htf_trend, self.lock)
                        except Exception:
                            htf_trend = None

                    with self.lock:
                        self.bot_state['symbols'][s]['price'] = curr_p
                        if htf_trend:
                            self.bot_state['symbols'][s]['htf_trend'] = htf_trend
                        self.bot_state['loss_streak'] = self.trades.loss_streak  # ✅ sinxronizatsiya
                        save_state(self.bot_state)
                        # ✅ Deploy: extras ham saqlanadi
                        save_extras(
                            self.telegram.price_alerts,
                            self.trades._sent_signals,
                            self.telegram.onboarding_done
                        )

                    # ✅ HTF (H1) ma'lumotlarini olish (Multi-Timeframe uchun)
                    htf_df = None
                    try:
                        htf_df = await self.exchange.fetch_ohlcv(s, '1h', limit=250)
                    except Exception:
                        pass  # HTF bo'lmasa neutral holatda ishlaydi

                    # ✅ Signal generatsiyasi (yangi SMC mantiq bilan)
                    from core.indicator import GeminiIndicator
                    ind = GeminiIndicator(self.cfg)
                    sig = ind.generate_signal(df, s, self.cfg.get('timeframe', '15m'), self.trades.loss_streak, htf_df=htf_df)
                    if not sig:
                        import random
                        if random.randint(1, 10) == 1: print(f"[LOG] {s} da hozircha SMC setup yo'q.")

                    min_q = self.cfg.get('smc', {}).get('min_quality', 75.0)
                    if sig and sig.quality >= min_q:
                        logger.info(f"🎯 [SIGNAL DETECTED] {s} | Quality: {sig.quality}% | Direction: {sig.direction}")
                        ai_review_enabled = self.bot_state.get('settings', {}).get('ai_review_enabled', True)
                        safe_ai_reason = None
                        
                        if ai_review_enabled:
                            logger.info(f"🤖 [AI REVIEW START] Sending {s} signal to Gemini for validation...")
                            sig_data = {
                                'symbol': s,
                                'direction': sig.direction,
                                'entry': round(float(sig.entry), 5),
                                'sl': round(float(sig.sl), 5),
                                'tp1': round(float(sig.tp1), 5),
                                'tp2': round(float(sig.tp2), 5) if sig.tp2 else None,
                                'tp3': round(float(sig.tp3), 5) if sig.tp3 else None,
                                'quality': sig.quality,
                                'reason': sig.reason,
                                'time_utc': datetime.now(timezone.utc).strftime('%H:%M')
                            }
                            # ✅ Grafik rasmini yaratish
                            from core.indicator import GeminiIndicator
                            chart_bytes = GeminiIndicator(self.cfg).draw_chart_bytes(df, s, sig)
                            is_appr, ai_reason = await self.telegram.ai.evaluate_trade_signal(sig_data, image_bytes=chart_bytes)
                            
                            import html
                            safe_ai_reason = html.escape(ai_reason) if ai_reason else ""

                            if not is_appr:
                                print(f"❌ [AI REJECT] {s} rad etildi.")
                                msg = f"❌ <b>AI RAD ETDI ({s}):</b>\n\n{safe_ai_reason}\n\n<i>Signal bekor qilindi (Savdoga kiritilmadi).</i>"
                                await self.telegram.send(msg)
                                continue
                            else:
                                print(f"✅ [AI APPROVE] {s} tasdiqlandi!")

                        # ✅ SPRINT 1 #5: Yangilik vaqtida signal bloki
                        news_active = False
                        try:
                            upcoming_news = await self.news.check_upcoming_news()
                            if upcoming_news:
                                news_active = True
                                logger.info(f"[NEWS FILTER] {s} signali bloklandi — kuchli yangilik vaqtida")
                        except Exception: pass

                        if news_active:
                            print(f"⚠️ [NEWS BLOCK] {s} — Yangilik vaqtida to'xtatildi.")
                            continue

                        # ✅ SPRINT 1 #1: Chart rasm generatsiyasi
                        chart_buf = None
                        try:
                            chart_buf = await generate_chart_buffer(df)
                        except Exception as e:
                            print(f"[CHART] Rasm generatsiyasida xato: {e}")

                        print(f"📤 [TELEGRAM] Xabar yuborilmoqda...")
                        await self.trades.process_and_send_signal(s, sig, self.bot_state, ai_reason=safe_ai_reason, chart_buf=chart_buf)
                        print(f"✅ [SUCCESS] {s} yuborildi!")
                elif sig:
                    print(f"[SKIP] {s} signal sifati past ({sig.quality}% < {min_q}%)")
                await asyncio.sleep(10)
            # ✅ Watchdog uchun heartbeat
            try:
                with open('data/heartbeat.txt', 'w') as f:
                    f.write(str(time.time()))
            except: pass

            # 🧬 [GENETIC EVOLUTION] Har 1 soatda sozlamalarni optimallashtirish
            if datetime.now() - self.last_evolution > timedelta(hours=1):
                try:
                    history = self.db.get_stats(limit=100).get('history', [])
                    if len(history) >= 5:
                        best_dna = self.optimizer.evolve(history)
                        new_q = round(best_dna['min_quality'], 1)
                        
                        if abs(self.cfg['smc'].get('min_quality', 75) - new_q) > 1.0:
                            print(f"[GENETIC] DNK yangilandi: Min Quality -> {new_q}%")
                            self.cfg['smc']['min_quality'] = new_q
                            with open('config/settings.yaml', 'w') as f:
                                yaml.dump(self.cfg, f)
                    self.last_evolution = datetime.now()
                except Exception as e:
                    print(f"[GENETIC ERROR] Evolyutsiya xatosi: {e}")

            print(f"[SYSTEM] Skanerlash yakunlandi ({datetime.now().strftime('%H:%M:%S')}). 3 daqiqa kutish...", flush=True)
            await asyncio.sleep(180)

    async def _news_loop(self):
        """Fundamental yangiliklarni kuzatish va xabar berish"""
        from utils.news import NewsWatcher
        self.news_watcher = NewsWatcher(self.cfg)
        print("[SYSTEM] Yangiliklar monitori faollashdi.")
        while True:
            try:
                upcoming = await self.news_watcher.check_upcoming_news()
                for item in upcoming:
                    msg = (
                        f"🚨 <b>MUHIM YANGILIK! (HIGH IMPACT)</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🌍 Davlat: {item.get('country')}\n"
                        f"📰 Voqea: {item.get('event')}\n"
                        f"⏰ Vaqt: {item.get('date')}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ Diqqat: Bu vaqtda bozorda volatillik oshishi mumkin!"
                    )
                    await self.telegram.send(msg)
                    print(f"[NEWS] {item.get('event')} yuborildi.")
            except Exception as e:
                print(f"[ERROR] News Loop: {e}")
            
            await asyncio.sleep(900)  # Har 15 daqiqada tekshirish

    async def _monitor_loop(self):
        """Virtual Monitoring: Berilgan signallarning natijasini (SL/TP) tekshirib boradi"""
        print("[MONITOR] Virtual Signal Monitor ishga tushdi...")
        while True:
            if self.bot_state.get('panic_request'):
                await asyncio.sleep(30)
                continue
            try:
                pending = self.db.get_pending_signals()
                if pending:
                    for sig_row in pending:
                        current_symbol = "Unknown"
                        try:
                            # sid, symbol, side, entry, sl, tp1 = sig
                            sid = sig_row[0]
                            current_symbol = sig_row[1]
                            side = sig_row[2]
                            entry = sig_row[3]
                            sl = sig_row[4]
                            tp1 = sig_row[5]
                            
                            # Eski versiyadagi (SL/TP kiritilmagan) signallarni o'tkazib yuborish
                            if sl is None or tp1 is None:
                                self.db.update_signal_result(sid, 'IGNORED (OLD)')
                                continue

                            # Joriy narxni olish (15m barqarorroq)
                            df_price = await self.exchange.fetch_ohlcv(current_symbol, '15m', limit=2)
                            if df_price is None or df_price.empty:
                                # Har bir muammo uchun exception otmaymiz, shunchaki keyingisiga o'tamiz
                                continue
                            price = df_price['close'].iloc[-1]
                            
                            result = None
                            if side.upper() == 'BUY':
                                if price >= tp1: result = 'WIN (TP1)'
                                elif price <= sl: result = 'LOSS (SL)'
                            else: # SELL
                                if price <= tp1: result = 'WIN (TP1)'
                                elif price >= sl: result = 'LOSS (SL)'
                            
                            if result:
                                self.db.update_signal_result(sid, result)
                                r_gain = float(self.cfg.get('tp', {}).get('tp1_mult', 1.5)) if 'WIN' in result else -1.0
                                self.db.add_history(datetime.now().strftime('%H:%M'), current_symbol, side.upper()=='BUY', entry, result, r_gain)
                                
                                # BALANSNI YANGILASH VA LOSS STREAK NI BOSHQARISH
                                with self.lock:
                                    curr_bal = self.bot_state.get('terminal', {}).get('balance', 5000.0)
                                    risk_pct = float(self.cfg.get('trend', {}).get('risk_perc', 2.0))
                                    risk_amount = curr_bal * (risk_pct / 100)
                                    
                                    if 'WIN' in result:
                                        profit_mult = float(self.cfg.get('tp', {}).get('tp1_mult', 1.5))
                                        new_bal = curr_bal + (risk_amount * profit_mult)
                                        self.trades.handle_win()
                                    else:
                                        new_bal = curr_bal - risk_amount
                                        self.trades.handle_loss()
                                    
                                    self.bot_state['terminal']['balance'] = round(new_bal, 2)
                                    self.bot_state['loss_streak'] = self.trades.loss_streak
                                    save_state(self.bot_state)
                                    save_extras(
                                        self.telegram.price_alerts,
                                        self.trades._sent_signals,
                                        self.telegram.onboarding_done
                                    )

                                await self.telegram.send(f"✅ <b>VIRTUAL NATIJA: {current_symbol}</b>\nNatija: {result}\nNarx: {price}\nYangi Balans: <b>${self.bot_state['terminal']['balance']}</b>")
                                print(f"[MONITOR] {current_symbol} natijasi: {result}")
                        except Exception as inner_e:
                            print(f"[MONITOR ERROR] {current_symbol} signalini tekshirishda xato: {inner_e}")
                            continue # Bitta signaldagi xato boshqalariga ta'sir qilmasligi kerak
                            
            except Exception as e:
                print(f"[MONITOR ERROR] Asosiy xato: {e}")
            
            await asyncio.sleep(300) # Har 5 daqiqada tekshiradi

    async def _webhook_loop(self):
        """Dashboard /webhook orqali kelgan signallarni o'qib AI tasdiqlash uchun jo'natish."""
        queue_file = 'data/webhook_queue.json'
        from collections import namedtuple
        from datetime import datetime
        import json, os

        SigObj = namedtuple('Signal', ['direction', 'entry', 'sl', 'tp1', 'tp2', 'tp3', 'quality', 'reason', 'timestamp'])
        
        while True:
            try:
                if os.path.exists(queue_file):
                    with open(queue_file, 'r') as f:
                        queue = json.load(f)
                    
                    if queue:
                        # Queue'ni darhol tozalash (Race condition oldini olish uchun)
                        with open(queue_file + '.tmp', 'w') as f:
                            json.dump([], f)
                        os.replace(queue_file + '.tmp', queue_file)
                        
                        for data in queue:
                            try:
                                sym = data.get('symbol', 'UNKNOWN')
                                ai_review_enabled = self.bot_state.get('settings', {}).get('ai_review_enabled', True)
                                ai_reason = None
                                
                                if ai_review_enabled:
                                    logger.info(f"🤖 Webhook signal AI tahliliga yuborilmoqda: {sym}")
                                    is_appr, ai_reason = await self.telegram.ai.evaluate_trade_signal(data)
                                    if not is_appr:
                                        msg = f"❌ <b>AI RAD ETDI ({sym}):</b>\n\n{ai_reason}\n\n<i>Signal bekor qilindi (Savdoga kiritilmadi).</i>"
                                        await self.telegram.send(msg)
                                        continue
                                
                                # Dummy Signal obyekti yaratamiz (manager.py qabul qilishi uchun)
                                sig_obj = SigObj(
                                    direction=data.get('direction', 'buy'),
                                    entry=float(data.get('entry', 0.0)),
                                    sl=float(data.get('sl', 0.0)),
                                    tp1=float(data.get('tp1', data.get('tp', 0.0))),
                                    tp2=float(data.get('tp2', data.get('tp', 0.0))),
                                    tp3=float(data.get('tp3', data.get('tp', 0.0))),
                                    quality=95.0, # Pine Script signals usually high quality
                                    reason=data.get('reason', 'Webhook TradingView Signal'),
                                    timestamp=datetime.now()
                                )
                                
                                # Telegramga yuborish
                                await self.trades.process_and_send_signal(sym, sig_obj, self.bot_state, ai_reason=ai_reason)
                                
                            except Exception as item_err:
                                logger.error(f"Webhook yozuvida xato: {item_err}")
                                
            except Exception as e:
                pass # Queue o'qish xatosi (ignore)
            
            await asyncio.sleep(2) # 2 soniyada bir tekshiradi


    async def _heartbeat_loop(self):
        """Sprint 1 #3: Bot ishlab turganini tasdiqlash (har 5 daqiqada log, har 1 soatda xabar)."""
        hour_counter = 0
        while True:
            await asyncio.sleep(300)  # 5 daqiqa
            hour_counter += 1
            # 12 * 5 daqiqa = 1 soat
            if hour_counter >= 12:
                hour_counter = 0
                from datetime import datetime, timezone, timedelta
                uzt = datetime.now(timezone.utc) + timedelta(hours=5)
                loss_str = self.bot_state.get('loss_streak', 0)
                # ✅ Heartbeat'da extras saqlash (sinxronizatsiya)
                save_extras(
                    self.telegram.price_alerts,
                    self.trades._sent_signals,
                    self.telegram.onboarding_done
                )
                msg = (
                    f"❤️ <b>Bot ishlayapti</b> | {uzt.strftime('%H:%M')} UZT\n"
                    f"📊 Ketma-ket zarar: {loss_str}\n"
                    f"🔍 Kuzatilyotgan: {len(self.cfg.get('symbols', []))} ta instrument"
                )
                try:
                    await self.telegram.send(msg)
                except Exception: pass
            
            # ✅ Watchdog uchun heartbeat faylini yangilash
            try:
                with open('data/heartbeat.txt', 'w') as f:
                    f.write(str(time.time()))
            except: pass

            logger.debug("[HEARTBEAT] OK")

    async def _price_alert_loop(self):
        """Sprint 3 #1: Price Alert — har 30 soniyada narxlarni tekshirish."""
        while True:
            try:
                await asyncio.sleep(30)
                for uid, alerts in list(self.telegram.price_alerts.items()):
                    remaining = []
                    for (sym, target_price, direction) in alerts:
                        curr_p = self.bot_state.get('symbols', {}).get(sym, {}).get('price', 0)
                        if curr_p <= 0:
                            remaining.append((sym, target_price, direction))
                            continue
                        triggered = abs(curr_p - target_price) / target_price < 0.001  # 0.1% ichida
                        if triggered:
                            msg = (
                                f"🔔 <b>PRICE ALERT!</b>\n\n"
                                f"Instrument: <b>{sym}</b>\n"
                                f"Belgilangan narx: <code>{target_price}</code>\n"
                                f"Joriy narx: <code>{curr_p:.5g}</code>\n\n"
                                f"<i>Alert avtomatik o'chirildi.</i>"
                            )
                            await self.telegram.send(msg, cid=uid)
                            # Alert trigger bo'lgandan keyin o'chiriladi
                        else:
                            remaining.append((sym, target_price, direction))
                    self.telegram.price_alerts[uid] = remaining
            except Exception as e:
                logger.error(f"[ALERT LOOP] Xato: {e}")

    async def run(self):
        # Telegram pollingni birinchi va alohida ishga tushiramiz
        tasks = [
            self.telegram.poll_updates(self.bot_state),
            self._market_loop(),
            self._ai_loop(),
            self._monitor_loop(),
            self._webhook_loop(),
            self._heartbeat_loop(),
            self._price_alert_loop()
        ]
        print("[SYSTEM] Barcha oqimlar (o'zaro bog'liq bo'lmagan) ishga tushirilmoqda...")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    bot_app = GeminiBot()
    
    # Dashboardni faqat lokalda yoqamiz (Serverda u xalaqit beradi)
    is_pa = "PYTHONANYWHERE_DOMAIN" in os.environ
    if not is_pa:
        try:
            from utils.dashboard import create_app
            import threading
            flask_app = create_app(bot_app.bot_state, bot_app.cfg, bot_app.lock)
            def run_flask():
                flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
            threading.Thread(target=run_flask, daemon=True).start()
            print("--> Localhost Dashboard ishga tushdi -> http://127.0.0.1:8080")
        except Exception as e:
            print(f"⚠️ Dashboard ogohlantirishi: {e}")

    # Botning asosiy halqasi (Asyncio) ishga tushadi
    print(f"Titan V27.2 A+ MASTER ENGINE IS LIVE! (Server: {'PA' if is_pa else 'Local'})", flush=True)
    try:
        asyncio.run(bot_app.run())
    except KeyboardInterrupt:
        print("\n[STOP] Bot foydalanuvchi tomonidan to'xtatildi (Ctrl+C).", flush=True)
    except Exception as e:
        print(f"\n[FATAL ERROR] Bot to'xtadi: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logger.critical(f"FATAL ERROR: {e}", exc_info=True)
    finally:
        print("[SYSTEM] Tizim yopilmoqda.", flush=True)
