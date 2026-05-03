import logging, asyncio, aiohttp, json, os, yaml, io
from utils.ai_engine import AIEngine
from utils.database import DatabaseManager

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, config, lock):
        self.cfg = config['telegram']; self.lock = lock
        is_pa = "PYTHONANYWHERE_DOMAIN" in os.environ
        self.proxy = "http://proxy.server:3128" if is_pa else None
        self.base = f"https://api.telegram.org/bot{self.cfg['bot_token']}"
        self.admins = [str(x).strip() for x in self.cfg.get('chat_id', [])]
        self.api_keys = config.get('gemini_ai', {}).get('api_keys', [])
        self.model_name = config.get('gemini_ai', {}).get('model', 'gemini-2.5-flash')
        self.ai = AIEngine(self.api_keys, self.model_name)
        self.db = DatabaseManager()
        self._session = None
        self.user_states = {}
        self.user_modules = {}
        self.temp_data = {}
        self.chat_history = {}
        self.MAX_HISTORY = 5
        self._yaml_lock = __import__('threading').Lock()
        # Sprint 3
        self.price_alerts: dict = {}   # {uid: [(sym, price, direction), ...]}
        self.onboarding_done: set = set()  # Birinchi marta /start bosganlar
    
    async def get_ai_analysis(self, prompt, uid, context="technical", image_data=None):
        """AI Engine ga tahlil so'rovini yuborish (Wrapper)."""
        return await self.ai.get_analysis(prompt, context_type=context, image_bytes=image_data)

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45))
        return self._session

    async def send(self, t, cid=None, kb=None):
        sess = await self.get_session()
        cids = [cid] if cid else self.admins
        for c in cids:
            for i in range(0, len(str(t)), 4000):
                chunk = t[i:i+4000]
                data = {'chat_id': c, 'text': chunk, 'parse_mode': 'HTML'}
                if kb and i == 0: data['reply_markup'] = kb
                for attempt in range(3):
                    try:
                        async with sess.post(f"{self.base}/sendMessage", proxy=self.proxy, json=data) as r:
                            if r.status == 200: break
                            elif r.status in (502, 503, 504): await asyncio.sleep(1.5)
                            else: break
                    except: await asyncio.sleep(1)
                await asyncio.sleep(0.3)

    async def send_action(self, cid, action="typing"):
        sess = await self.get_session()
        try:
            async with sess.post(f"{self.base}/sendChatAction", proxy=self.proxy, json={'chat_id': cid, 'action': action}) as r:
                return r.status == 200
        except: return False

    async def send_photo(self, photo: bytes, caption: str = "", cid=None, kb=None):
        """Chart rasmini caption bilan yuborish."""
        import aiohttp as _aiohttp
        sess = await self.get_session()
        cids = [cid] if cid else self.admins
        for c in cids:
            try:
                data = _aiohttp.FormData()
                data.add_field('chat_id', str(c))
                data.add_field('caption', caption[:1024])
                data.add_field('parse_mode', 'HTML')
                if kb: data.add_field('reply_markup', kb)
                data.add_field('photo', photo, filename='chart.png', content_type='image/png')
                async with sess.post(f"{self.base}/sendPhoto", proxy=self.proxy, data=data) as r:
                    if r.status != 200:
                        await self.send(caption, cid=c, kb=kb)  # fallback
            except Exception as e:
                logger.warning(f"send_photo error: {e}")
                await self.send(caption, cid=c, kb=kb)

    async def poll_updates(self, bs):
        off = 0
        off_file = ".tg_offset"
        try:
            if os.path.exists(off_file):
                with open(off_file) as f: off = int(f.read().strip() or 0)
        except: off = 0
        while True:
            try:
                with open('config/settings.yaml', 'r') as f:
                    cfg_full = yaml.safe_load(f)
                sess = await self.get_session()
                async with sess.get(f"{self.base}/getUpdates?offset={off+1}&timeout=30", proxy=self.proxy) as r:
                    if r.status == 200:
                        res = await r.json()
                        for u in res.get('result', []):
                            off = await self.handle_update(u, bs, cfg_full, sess, off_file)
                    else:
                        await asyncio.sleep(5)
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(5)

    async def handle_update(self, u, bs, cfg_full, sess, off_file):
        """Yagona update qayta ishlash (TDD uchun ajratilgan)"""
        off = u['update_id']; m = u.get('message', {}); cb = u.get('callback_query', {})
        uid = str(cb.get('from', m.get('from', {})).get('id', ''))
        is_admin = uid in self.admins
        current_state = self.user_states.get(uid)
        sym_list = cfg_full.get('symbols', ["XAU/USD", "BTC/USDT"])

        try:
            with open(off_file, 'w') as f: f.write(str(off))
        except: pass

        # ── KEYBOARD LAYOUTS ────────────────────────────────────────────────
        ADMIN_KB = {'keyboard': [
            [{'text': "📊 Texnik Tahlil"}, {'text': "🌐 Fundamental"}],
            [{'text': "👨‍🏫 Jonli SMC Trener"}, {'text': "💬 AI Chat Assistant"}],
            [{'text': "⚡ Scalping AI"}, {'text': "📈 Hisobot (Analytics)"}],
            [{'text': "⚙️ Sozlamalar"}, {'text': "⚖️ Risk Status"}],
            [{'text': "📖 Qo'llanma"}, {'text': "🧪 Test Signal"}],
            [{'text': "🚨 PANIC CLOSE ALL"}]
        ], 'resize_keyboard': True}

        USER_KB = {'keyboard': [
            [{'text': "📊 Texnik Tahlil"}, {'text': "🌐 Fundamental"}],
            [{'text': "👨‍🏫 Jonli SMC Trener"}, {'text': "💬 AI Chat Assistant"}],
            [{'text': "📈 Hisobot (Analytics)"}, {'text': "📖 Qo'llanma"}]
        ], 'resize_keyboard': True}

        KB = json.dumps(ADMIN_KB if is_admin else USER_KB)

        # ── CALLBACK QUERIES ─────────────────────────────────────────────────
        if cb:
            d = cb['data']

            # Trener modullari
            if d.startswith("mentor_"):
                if d == "mentor_exit":
                    self.user_states.pop(uid, None)
                    self.user_modules.pop(uid, None)
                    await self.send("🚪 Trener rejimidan chiqdingiz.", cid=uid, kb=KB)
                else:
                    self.user_states[uid] = "in_session"
                    self.user_modules[uid] = d
                    texts = {
                        "mentor_lessons": "📚 <b>Mavzuli Darslar</b> faollashdi.\n\nQaysi mavzudan boshlaymiz?",
                        "mentor_live_examples": "🌐 <b>Jonli Misollar</b> faollashdi.\n\nSavolingizni yo'llang:",
                        "mentor_qa": "❓ <b>Erkin Savol-Javob</b> faollashdi.\n\nSMC bo'yicha savolingizni bering:"
                    }
                    await self.send(texts.get(d, "Trener faol."), cid=uid)

            # TP/SL/Skip natijasi callback
            elif d.startswith("sig_tp:") or d.startswith("sig_sl:") or d.startswith("sig_skip:"):
                parts = d.split(":")
                result_type = parts[0].replace("sig_", "")
                sig_id = parts[1] if len(parts) > 1 else "?"
                sym = parts[2] if len(parts) > 2 else "?"
                result_map = {
                    "tp":   ("✅ TP",  "Tabriklaymiz! Take Profit urdi."),
                    "sl":   ("❌ SL",  "Zarar qayd qilindi. Risk menejmenti davom etadi."),
                    "skip": ("⏭ Skip", "Signal o'tkazib yuborildi.")
                }
                label, comment = result_map.get(result_type, ("?", ""))
                # DB ga natijani yozish
                try:
                    self.db.mark_signal_result(sig_id, result_type)
                except Exception: pass
                await self.send(
                    f"{label} — <b>{sym}</b>\n{comment}\n\n"
                    f"<i>Natija qayd qilindi. Statistika yangilandi.</i>",
                    cid=uid
                )

            # AI tahlil so'rovi
            elif d.startswith("ai_"):
                if "scalping" in d and not is_admin:
                    await sess.post(f"{self.base}/answerCallbackQuery", json={
                        'callback_query_id': cb['id'], 'text': "❌ Scalping faqat adminlar uchun.", 'show_alert': True})
                    return off
                t_type, sym = d.replace("ai_", "").split(":")
                with self.lock: bs['ai_requests'].append({'type': t_type, 'symbol': sym, 'chat_id': uid})
                await self.send(f"⏳ <i>{sym} uchun {t_type.upper()} tahlili tayyorlanmoqda...</i>", cid=uid)

            # ── SOZLAMALAR INLINE ──
            elif d == "sym_list":
                syms = cfg_full.get('symbols', [])
                text = "🪙 <b>Joriy instrumentlar:</b>\n\n" + "\n".join([f"• <code>{s}</code>" for s in syms])
                ikb = {'inline_keyboard': [[
                    {'text': "➕ Qo'shish", 'callback_data': "sym_add"},
                    {'text': "❌ O'chirish", 'callback_data': "sym_rem"}
                ]]}
                await self.send(text, cid=uid, kb=json.dumps(ikb))

            elif d == "sym_add" and is_admin:
                self.user_states[uid] = "wait_sym_add"
                await self.send("➕ <b>Yangi instrument qo'shish:</b>\n\nNomini kiriting (masalan: <code>SOL/USDT</code>):", cid=uid)

            elif d == "sym_rem" and is_admin:
                syms = cfg_full.get('symbols', [])
                ikb = {'inline_keyboard': [[{'text': f"❌ {s}", 'callback_data': f"sym_del:{s}"}] for s in syms]}
                await self.send("❌ <b>O'chirish uchun tanlang:</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("sym_del:") and is_admin:
                target = d.replace("sym_del:", "")
                if target in cfg_full.get('symbols', []):
                    cfg_full['symbols'].remove(target)
                    with self._yaml_lock:
                        with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                    await self.send(f"✅ <code>{target}</code> ro'yxatdan o'chirildi.", cid=uid)

            elif d == "tf_menu":
                ikb = {'inline_keyboard': [
                    [{'text': "5m",  'callback_data': "tf_5m"},  {'text': "15m", 'callback_data': "tf_15m"}],
                    [{'text': "1h",  'callback_data': "tf_1h"},  {'text': "4h",  'callback_data': "tf_4h"}]
                ]}
                await self.send("⏱ <b>Ishchi taymfreymni tanlang:</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("tf_") and d != "tf_menu" and is_admin:
                new_tf = d.replace("tf_", "")
                cfg_full['timeframe'] = new_tf
                with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                await self.send(f"✅ Ishchi taymfreym <b>{new_tf}</b> ga o'zgartirildi.", cid=uid)

            elif d == "risk_menu":
                ikb = {'inline_keyboard': [
                    [{'text': "0.5%", 'callback_data': "risk_0.5"}, {'text': "1.0%", 'callback_data': "risk_1.0"}],
                    [{'text': "2.0%", 'callback_data': "risk_2.0"}, {'text': "3.0%", 'callback_data': "risk_3.0"}],
                    [{'text': "5.0%", 'callback_data': "risk_5.0"}]
                ]}
                await self.send("💰 <b>Har bir bitim uchun riskni tanlang:</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("risk_") and d != "risk_menu" and is_admin:
                try:
                    new_r = float(d.replace("risk_", ""))
                    if 'trend' not in cfg_full: cfg_full['trend'] = {}
                    cfg_full['trend']['risk_perc'] = new_r
                    with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                    await self.send(f"✅ Har bir bitim uchun risk: <b>{new_r}%</b> ga o'zgartirildi.", cid=uid)
                except: pass

            elif d == "qual_menu":
                curr_q = cfg_full.get('smc', {}).get('min_quality', 75.0)
                ikb = {'inline_keyboard': [
                    [{'text': "🟢 30%", 'callback_data': "setqual_30.0"}, {'text': "🟡 50%", 'callback_data': "setqual_50.0"}],
                    [{'text': "🟠 75%", 'callback_data': "setqual_75.0"}, {'text': "🔴 90%", 'callback_data': "setqual_90.0"}],
                    [{'text': "🗑 Statistikani tozalash", 'callback_data': "clear_stats_confirm"}]
                ]}
                await self.send(f"⚙️ <b>Sifat Sozlamasi</b>\n\nJoriy: {curr_q}%", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("setqual_") and is_admin:
                try:
                    new_q = float(d.replace("setqual_", ""))
                    if 'smc' not in cfg_full: cfg_full['smc'] = {}
                    cfg_full['smc']['min_quality'] = new_q
                    with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                    await self.send(f"✅ Sifat chegarasi <b>{new_q}%</b> ga o'zgartirildi.", cid=uid)
                except: pass

            elif d == "clear_stats_confirm" and is_admin:
                self.db.clear_all_stats()
                await self.send("✅ Barcha statistika va signallar tarixi muvaffaqiyatli tozalandi!", cid=uid)

            elif d == "set_balance_menu" and is_admin:
                self.user_states[uid] = "wait_balance_set"
                curr_b = bs.get('terminal', {}).get('balance', 0)
                await self.send(f"⚖️ <b>Joriy balans: ${curr_b}</b>\n\nYangi soxta balans kiriting (masalan: 5000):", cid=uid)

            elif d == "toggle_ai_review" and is_admin:
                if 'settings' not in bs: bs['settings'] = {}
                cur = bs.get('settings', {}).get('ai_review_enabled', True)
                bs['settings']['ai_review_enabled'] = not cur
                status = "YOQILDI ✅" if bs['settings']['ai_review_enabled'] else "O'CHIRILDI 🔴"
                from utils.persistence import save_state
                save_state(bs)
                await self.send(f"🤖 AI Xulosasi <b>{status}</b>.", cid=uid)

            elif d == "today_signals":
                sigs = self.db.get_today_signals()
                if not sigs:
                    await self.send("📋 <b>Bugungi signallar:</b>\n\n⏳ Hali signal yuborilmagan.", cid=uid)
                else:
                    lines = [f"📋 <b>Bugungi Signallar ({len(sigs)} ta):</b>\n"]
                    for s2 in sigs:
                        icon = {"WIN": "✅", "LOSS": "❌", "SKIP": "⏭", "PENDING": "⏳"}.get(s2['result'], "•")
                        lines.append(
                            f"{icon} <b>{s2['symbol']}</b> {s2['direction']} "
                            f"@ <code>{s2['entry']:.5g}</code> "
                            f"[{s2['quality']}%] {s2['time'][11:16]}"
                        )
                    await self.send("\n".join(lines), cid=uid)

            elif d == "monthly_pnl":
                d7  = self.db.get_period_pnl(days=7)
                d30 = self.db.get_period_pnl(days=30)
                msg = (
                    f"📈 <b>P&L Hisoboti (R-hisobida):</b>\n\n"
                    f"📅 <b>So'nggi 7 kun:</b>\n"
                    f"   ✅ TP: {d7['tp']} | ❌ SL: {d7['sl']} | ⏭ Skip: {d7['skip']}\n"
                    f"   🏆 Win-Rate: <b>{d7['winrate']}%</b> | Jami: {d7['total_r']:+.1f}R\n\n"
                    f"📅 <b>So'nggi 30 kun:</b>\n"
                    f"   ✅ TP: {d30['tp']} | ❌ SL: {d30['sl']} | ⏭ Skip: {d30['skip']}\n"
                    f"   🏆 Win-Rate: <b>{d30['winrate']}%</b> | Jami: {d30['total_r']:+.1f}R\n\n"
                    f"<i>⏳ Faqat TP/SL belgilangan signallar hisoblanadi.</i>"
                )
                await self.send(msg, cid=uid)

            # Sprint 3: Signal tarixi (oxirgi 10 ta)
            elif d == "signal_history":
                sigs = self.db.get_today_signals()
                if not sigs:
                    # Oxirgi 7 kundan qidirish
                    conn = self.db._get_conn()
                    try:
                        rows = conn.execute(
                            "SELECT time, symbol, direction, entry, quality, result "
                            "FROM signals ORDER BY id DESC LIMIT 10"
                        ).fetchall()
                    finally:
                        conn.close()
                    if not rows:
                        await self.send("📜 <b>Signallar tarixi:</b>\n\n⏳ Hali signal yo'q.", cid=uid)
                    else:
                        lines = ["📜 <b>Oxirgi signallar:</b>\n"]
                        for r in rows:
                            icon = {"WIN":"✅","LOSS":"❌","SKIP":"⏭","PENDING":"⏳"}.get(r[5],"•")
                            lines.append(f"{icon} <b>{r[1]}</b> {r[2]} @ <code>{r[3]:.5g}</code> [{r[4]}%] {r[0][5:16]}")
                        await self.send("\n".join(lines), cid=uid)
                else:
                    lines = ["📜 <b>Bugungi Signallar:</b>\n"]
                    for s2 in sigs[:10]:
                        icon = {"WIN":"✅","LOSS":"❌","SKIP":"⏭","PENDING":"⏳"}.get(s2['result'],"•")
                        lines.append(f"{icon} <b>{s2['symbol']}</b> {s2['direction']} @ <code>{s2['entry']:.5g}</code> [{s2['quality']}%] {s2['time'][11:16]}")
                    await self.send("\n".join(lines), cid=uid)

            # Sprint 3: Price Alert ro'yxati
            elif d == "alert_list":
                alerts = self.price_alerts.get(uid, [])
                if not alerts:
                    msg = "🔔 <b>Alert ro'yxati:</b>\n\n⏳ Hozircha alert o'rnatilmagan."
                else:
                    lines = ["🔔 <b>Aktiv Alertlar:</b>\n"]
                    for i, (sym, price, direction) in enumerate(alerts):
                        lines.append(f"{i+1}. <b>{sym}</b> {direction} <code>{price}</code>")
                    msg = "\n".join(lines)
                ikb = {'inline_keyboard': [
                    [{'text': "➕ Yangi Alert", 'callback_data': "alert_add"}],
                    [{'text': "🗑 Hammasini O'chir", 'callback_data': "alert_clear"}]
                ]}
                await self.send(msg, cid=uid, kb=json.dumps(ikb))

            elif d == "alert_add":
                self.user_states[uid] = "wait_alert_sym"
                await self.send(
                    "🔔 <b>Yangi Price Alert:</b>\n\n"
                    "1-qadam: Instrument nomini kiriting\n"
                    "Masalan: <code>XAU/USD</code> yoki <code>BTC/USDT</code>", cid=uid)

            elif d == "alert_clear":
                self.price_alerts.pop(uid, None)
                await self.send("✅ Barcha alertlar o'chirildi.", cid=uid)

            # Sprint 3: Vaqt zonasi
            elif d == "tz_menu":
                ikb = {'inline_keyboard': [
                    [{'text': "🇺🇿 UTC+5 (UZT)",  'callback_data': "tz_set:5"},
                     {'text': "🇹🇷 UTC+3 (MSK)",  'callback_data': "tz_set:3"}],
                    [{'text': "🇦🇪 UTC+2 (EET)",  'callback_data': "tz_set:2"},
                     {'text': "🇦🇪 UTC+0 (GMT)",  'callback_data': "tz_set:0"}],
                    [{'text': "🇦🇪 UTC+8 (SGT)",  'callback_data': "tz_set:8"}]
                ]}
                curr_tz = bs.get('settings', {}).get('tz_offset', 5)
                await self.send(f"🌍 <b>Vaqt Zonasi (joriy: UTC+{curr_tz}):</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("tz_set:"):
                tz_offset = int(d.replace("tz_set:", ""))
                if 'settings' not in bs: bs['settings'] = {}
                bs['settings']['tz_offset'] = tz_offset
                from utils.persistence import save_state
                save_state(bs)
                await self.send(f"✅ Vaqt zonasi <b>UTC+{tz_offset}</b> ga o'zgartirildi.", cid=uid)

            elif d == "stat_winrate":
                st = self.db.get_stats(limit=100)
                if st['total'] == 0:
                    msg = (f"📊 <b>Statistika (Faqat Signallar):</b>\n\n"
                           f"📈 Jami yuborilgan signallar: <b>{st.get('total_signals', 0)} ta</b>\n"
                           f"⏳ Savdo natijalari kutilmoqda...")
                else:
                    msg = (f"📊 <b>Signal Statistikasi (Oxirgi {st['total']} ta):</b>\n\n"
                           f"✅ Foyda (TP): {st['tp']}\n"
                           f"❌ Zarar (SL): {st['sl']}\n"
                           f"📈 Jami signallar: {st.get('total_signals', 0)}\n\n"
                           f"🏆 <b>Win-Rate: {st['winrate']}%</b>\n"
                           f"💰 Jami foyda: {st['profit']} R")
                await self.send(msg, cid=uid)

            try: await sess.post(f"{self.base}/answerCallbackQuery", proxy=self.proxy, json={'callback_query_id': cb['id']})
            except: pass
            return off

        # ── MESSAGES ─────────────────────────────────────────────────────────
        elif m:
            t = m.get('text', '')

            if not t and not m.get('photo') and not m.get('document'): return off

            if t == "/start":
                self.user_states.pop(uid, None)
                self.user_modules.pop(uid, None)
                if is_admin:
                    with self.lock: bs['panic_request'] = False
            
            # ✅ Xavfsizlik filtri: Agar menyu tugmasi bosilsa, har qanday kutish holatini bekor qilish
            MENU_BUTTONS = [
                "📊 Texnik Tahlil", "🌐 Fundamental", "👨‍🏫 Jonli SMC Trener", 
                "💬 AI Chat Assistant", "⚡ Scalping AI", "📈 Hisobot", 
                "⚙️ Sozlamalar", "⚖️ Risk Status", "📖 Qo'llanma", 
                "🧪 Test Signal", "🚨 PANIC CLOSE ALL"
            ]
            if any(btn in t for btn in MENU_BUTTONS):
                self.user_states.pop(uid, None)
                current_state = None # Holatni reset qilamiz
                # Sprint 3 #4: Onboarding — birinchi marta bosganlar uchun
                if uid not in self.onboarding_done:
                    self.onboarding_done.add(uid)
                    onboard = (
                        "🚀 <b>GEMINI SMC TITAN V27.2 ga xush kelibsiz!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "📖 <b>Qanday foydalanish kerak:</b>\n\n"
                        "➕ <b>1-qadam:</b> \"\ud83d� Texnik Tahlil\" → instrument tanlang\n"
                        "➕ <b>2-qadam:</b> Signal avtomatik keladi (sifat ≥75%)\n"
                        "➕ <b>3-qadam:</b> Signal natijasida \u2705 TP yoki \u274c SL bosing\n"
                        "➕ <b>4-qadam:</b> \u2764️ Bot har soat ishlayotganini tasdiqlaydi\n\n"
                        "ℹ️ <b>Yordam:</b> \"\ud83d� Qo'llanma\" tugmasini bosing"
                    )
                    await self.send(onboard, cid=uid)
                await self.send("<b>V27.2 A+ TITAN MASTER</b> botiga xush kelibsiz! 🚀", cid=uid, kb=KB)
                return off

            # FSM: Alert — Instrument kutish
            if current_state == "wait_alert_sym" and t:
                self.temp_data[uid] = {'alert_sym': t.upper().strip()}
                self.user_states[uid] = "wait_alert_price"
                await self.send(
                    f"🔔 Instrument: <b>{t.upper().strip()}</b>\n\n"
                    "2-qadam: Narxni kiriting\n"
                    "Masalan: <code>2400.50</code>", cid=uid)
                return off

            if current_state == "wait_alert_price" and t:
                try:
                    target_price = float(t.strip().replace(',', '.'))
                    sym = self.temp_data.get(uid, {}).get('alert_sym', '?')
                    if uid not in self.price_alerts: self.price_alerts[uid] = []
                    # Maksimal 10 ta alert
                    if len(self.price_alerts[uid]) >= 10:
                        self.price_alerts[uid].pop(0)
                    self.price_alerts[uid].append((sym, target_price, '↔️ any'))
                    self.user_states.pop(uid, None)
                    self.temp_data.pop(uid, None)
                    await self.send(
                        f"✅ <b>Alert o'rnatildi:</b>\n"
                        f"Instrument: <b>{sym}</b>\n"
                        f"Narx: <code>{target_price}</code>\n\n"
                        f"<i>Narx bu darajaga yetganda xabar olasiz.</i>", cid=uid)
                except ValueError:
                    await self.send("❌ Xato format. Faqat raqam kiriting (masalan: <code>2400.50</code>).", cid=uid)
                return off

            if current_state == "wait_sym_add" and is_admin:
                sym_name = t.upper().strip()
                if "/" in sym_name and len(sym_name) < 15:
                    if sym_name not in cfg_full.get('symbols', []):
                        cfg_full['symbols'].append(sym_name)
                        with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                        await self.send(f"✅ <code>{sym_name}</code> instrumentlar ro'yxatiga qo'shildi.", cid=uid)
                    else:
                        await self.send(f"⚠️ <code>{sym_name}</code> allaqachon mavjud.", cid=uid)
                else:
                    await self.send("❌ Xato format. Masalan: <code>SOL/USDT</code>", cid=uid)
                self.user_states.pop(uid, None)
                return off

            # FSM: Balans kiritish kutish
            if current_state == "wait_balance_set" and is_admin:
                try:
                    new_bal = float(t.strip())
                    if new_bal < 0: raise ValueError
                    with self.lock:
                        if 'terminal' not in bs: bs['terminal'] = {}
                        bs['terminal']['balance'] = new_bal
                    from utils.persistence import save_state
                    save_state(bs)
                    await self.send(f"✅ <b>Yangi soxta balans o'rnatildi: ${new_bal}</b>", cid=uid)
                except ValueError:
                    await self.send("❌ Xato! Faqat musbat raqam kiriting (masalan: 5000).", cid=uid)
                self.user_states.pop(uid, None)
                return off

            # FSM: Session ichida (Trener/Chat)
            if current_state == "in_session":
                if t and t.lower() in ["chiqish", "exit", "stop", "/stop"]:
                    self.user_states.pop(uid, None)
                    self.user_modules.pop(uid, None)
                    await self.send("🚪 Trener rejimidan chiqdingiz.", cid=uid, kb=KB)
                    return off

                img_data = None
                if m.get('photo'):
                    fid = m['photo'][-1]['file_id']
                    async with sess.get(f"{self.base}/getFile?file_id={fid}", proxy=self.proxy) as gr:
                        if gr.status == 200:
                            fpath = (await gr.json())['result']['file_path']
                            async with sess.get(f"https://api.telegram.org/file/bot{self.cfg['bot_token']}/{fpath}", proxy=self.proxy) as dr:
                                img_data = await dr.read() if dr.status == 200 else None

                # ✅ Sprint 3: PDF va Word fayllarni tahlil qilish
                doc = m.get('document')
                if doc and current_state == "in_session":
                    fname = doc.get('file_name', '').lower()
                    fid = doc['file_id']
                    valid_exts = ['.pdf', '.docx', '.csv', '.json', '.xlsx', '.xls']
                    if any(fname.endswith(ext) for ext in valid_exts):
                        await self.send(f"📄 <b>{fname}</b> yuklanmoqda va tahlil qilinmoqda...", cid=uid)
                        async with sess.get(f"{self.base}/getFile?file_id={fid}", proxy=self.proxy) as gr:
                            if gr.status == 200:
                                fpath = (await gr.json())['result']['file_path']
                                async with sess.get(f"https://api.telegram.org/file/bot{self.cfg['bot_token']}/{fpath}", proxy=self.proxy) as dr:
                                    if dr.status == 200:
                                        file_bytes = await dr.read()
                                        extracted_text = ""
                                        try:
                                            if fname.endswith('.pdf'):
                                                from PyPDF2 import PdfReader
                                                reader = PdfReader(io.BytesIO(file_bytes))
                                                extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                                            elif fname.endswith('.docx'):
                                                from docx import Document
                                                doc_obj = Document(io.BytesIO(file_bytes))
                                                extracted_text = "\n".join([p.text for p in doc_obj.paragraphs])
                                            elif fname.endswith('.csv'):
                                                import pandas as pd
                                                df_csv = pd.read_csv(io.BytesIO(file_bytes))
                                                extracted_text = df_csv.head(50).to_string() # Dastlabki 50 qator
                                            elif fname.endswith('.json'):
                                                extracted_text = json.dumps(json.loads(file_bytes), indent=2, ensure_ascii=False)[:3000]
                                            elif fname.endswith(('.xlsx', '.xls')):
                                                import pandas as pd
                                                df_xl = pd.read_excel(io.BytesIO(file_bytes))
                                                extracted_text = df_xl.head(50).to_string()
                                            
                                            if extracted_text:
                                                t = f"Fayl mazmuni ({fname}):\n\n{extracted_text[:3000]}" # Limit 3k char
                                            else:
                                                await self.send("⚠️ Fayldan matn ajratib bo'lmadi.", cid=uid)
                                                return off
                                        except Exception as e:
                                            await self.send(f"❌ Faylni o'qishda xato: {e}", cid=uid)
                                            return off
                    else:
                        await self.send("⚠️ Faqat .pdf, .docx, .csv, .json va .xlsx fayllar qabul qilinadi.", cid=uid)
                        return off

                user_text = t or m.get('caption', '') or "Ushbu rasmni tahlil qiling."
                with self.lock: bs['ai_requests'].append({
                    'type': self.user_modules.get(uid, 'mentor_qa'),
                    'symbol': 'SMC', 'chat_id': uid,
                    'text': user_text, 'image': img_data
                })
                await self.send("🧠 [AI tahlil qilmoqda...]", cid=uid)
                return off

            # ── ASOSIY MENYU TUGMALARI ───────────────────────────────────────

            if "Sozlamalar" in t and is_admin:
                ai_enabled = bs.get('settings', {}).get('ai_review_enabled', True)
                ai_btn = "🤖 AI Xulosa: 🟢 YOQ" if ai_enabled else "🤖 AI Xulosa: 🔴 O'CH"
                ikb = {'inline_keyboard': [
                    [{'text': "🪙 Instrumentlar", 'callback_data': "sym_list"},
                     {'text': "⏱ Taymfreym",     'callback_data': "tf_menu"}],
                    [{'text': "💰 Risk %",         'callback_data': "risk_menu"},
                     {'text': "⚙️ Sifat",          'callback_data': "qual_menu"}],
                    [{'text': "📊 Statistika (Win-rate)", 'callback_data': "stat_winrate"},
                     {'text': "⚖️ Balans",        'callback_data': "set_balance_menu"}],
                    [{'text': "📋 Bugungi Signallar", 'callback_data': "today_signals"},
                     {'text': "📈 Oylik P&L",       'callback_data': "monthly_pnl"}],
                    [{'text': "📜 Signal Tarixi",   'callback_data': "signal_history"},
                     {'text': "🔔 Price Alert",    'callback_data': "alert_list"}],
                    [{'text': "🌍 Vaqt Zonasi",     'callback_data': "tz_menu"},
                     {'text': ai_btn,               'callback_data': "toggle_ai_review"}]
                ]}
                await self.send("⚙️ <b>Bot Sozlamalari:</b>", cid=uid, kb=json.dumps(ikb))

            elif "Jonli SMC Trener" in t:
                self.user_states[uid] = "choosing_module"
                ikb = {'inline_keyboard': [
                    [{'text': "📚 Mavzuli Darslar",    'callback_data': "mentor_lessons"}],
                    [{'text': "🌐 Jonli Misollar",      'callback_data': "mentor_live_examples"}],
                    [{'text': "❓ Erkin Savol-Javob",   'callback_data': "mentor_qa"}],
                    [{'text': "🚪 Chiqish",             'callback_data': "mentor_exit"}]
                ]}
                await self.send("👨‍🏫 <b>Jonli SMC Trener</b> rejimi:\n\nQaysi modulni tanlaysiz?", cid=uid, kb=json.dumps(ikb))

            elif any(x in t for x in ["Texnik Tahlil", "Fundamental", "Scalping"]):
                if "Scalp" in t and not is_admin:
                    await self.send("❌ Scalping AI faqat adminlar uchun.", cid=uid)
                    return off
                type_ai = 'fundamental' if 'Fund' in t else ('scalping' if 'Scalp' in t else 'technical')
                ikb = {'inline_keyboard': [[{'text': s, 'callback_data': f"ai_{type_ai}:{s}"}] for s in sym_list]}
                await self.send(f"🔍 <b>{type_ai.upper()}</b> uchun instrumentni tanlang:", cid=uid, kb=json.dumps(ikb))

            elif any(x in t for x in ["Chat Assistant", "AI Chat"]):
                self.user_states[uid] = "in_session"
                self.user_modules[uid] = "chat"
                await self.send("💬 <b>AI Chat Assistant</b> faollashdi. Savolingizni yozing:", cid=uid)

            elif any(x in t for x in ["Hisobot", "Analytics"]):
                await self.send("📈 <i>AI hisobot tuzmoqda...</i>", cid=uid)
                with self.lock: bs['ai_requests'].append({'type': 'analytics', 'symbol': 'ALL', 'chat_id': uid, 'text': 'Full report'})

            elif "PANIC" in t.upper() and is_admin:
                with self.lock: bs['panic_request'] = True
                await self.send("🚨 <b>EMERGENCY CALLED! Barcha savdolar to'xtatildi!</b>", cid=uid)

            elif "Risk Status" in t and is_admin:
                with self.lock:
                    b = bs.get('terminal', {}).get('balance', 0)
                    streak = bs.get('loss_streak', 0)
                msg = (f"⚖️ <b>JORIY RISK HOLATI:</b>\n\n"
                       f"💰 Kutilayotgan Balans: <b>${b}</b>\n"
                       f"📉 Ketma-ket Zararlar: <b>{streak}</b>\n")
                if streak >= 3:
                    msg += "\n⚠️ <b>DIQQAT! Katta ketma-ket zarar! Riskni kamaytiring.</b>"
                else:
                    msg += "\n✅ <b>Holat barqaror. Risk menejmenti nazoratda.</b>"
                await self.send(msg, cid=uid)

            elif "Test Signal" in t and is_admin:
                from datetime import datetime, timezone
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
                self.db.add_signal(now_str, 'EUR/USD', 'BUY', 1.0500, 1.0480, 1.0560, 95.0, "Manual Test Signal")
                await self.send("🧪 <b>TEST SIGNAL YARATILDI:</b>\n\nInstrument: EUR/USD\nHolat: BUY\nEntry: 1.0500\nSL: 1.0480\nTP: 1.0560", cid=uid)

            elif "llanma" in t.lower():
                guide = (
                    "📖 <b>GEMINI SMC TITAN V27.2 — Qo'llanma</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📊 <b>Texnik Tahlil</b> — SMC strukturani AI izohlaydi.\n"
                    "🌐 <b>Fundamental</b> — Global yangiliklar tahlili.\n"
                    "⚡ <b>Scalping AI</b> — Tezkor M5 signallar (Admin).\n"
                    "👨‍🏫 <b>SMC Trener</b> — AI mentor, chart tahlili.\n"
                    "💬 <b>AI Chat</b> — Erkin savol-javob + rasm tahlili.\n"
                    "📈 <b>Hisobot</b> — Signal statistikasi.\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "⚙️ <b>Sozlamalar (Admin):</b>\n"
                    "• 🪙 Instrumentlar — Juftliklar boshqaruvi\n"
                    "• ⏱ Taymfreym — 5m/15m/1h/4h\n"
                    "• 💰 Risk % — 0.5% dan 5% gacha\n"
                    "• ⚙️ Sifat — Signal filtri (30%-90%)\n"
                    "• 📊 Statistika — Win-rate ko'rish\n"
                    "• 🤖 AI Xulosa — ON/OFF toggle\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💡 <i>Chart rasmi yuborib tahlil qildirish mumkin!</i>"
                )
                await self.send(guide, cid=uid)

            elif not t.startswith('/') or m.get('photo'):
                img_data = None
                if m.get('photo'):
                    fid = m['photo'][-1]['file_id']
                    async with sess.get(f"{self.base}/getFile?file_id={fid}", proxy=self.proxy) as gr:
                        if gr.status == 200:
                            fpath = (await gr.json())['result']['file_path']
                            async with sess.get(f"https://api.telegram.org/file/bot{self.cfg['bot_token']}/{fpath}", proxy=self.proxy) as dr:
                                img_data = await dr.read() if dr.status == 200 else None

                if uid not in self.chat_history: self.chat_history[uid] = []
                user_text = t or m.get('caption', '') or "Tahlil."
                self.chat_history[uid].append({'role': 'user', 'text': user_text})
                if len(self.chat_history[uid]) > self.MAX_HISTORY:
                    self.chat_history[uid] = self.chat_history[uid][-self.MAX_HISTORY:]
                with self.lock: bs['ai_requests'].append({
                    'type': 'chat', 'symbol': 'KB',
                    'chat_id': uid, 'text': user_text, 'image': img_data
                })
                await self.send("⏳ Tahlil boshlandi...", cid=uid)

        return off
