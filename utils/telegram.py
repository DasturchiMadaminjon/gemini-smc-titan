import logging, asyncio, aiohttp, json, os, yaml, io
from utils.ai_engine import AIEngine
from utils.database import DatabaseManager

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, config, lock):
        self.cfg = config.get('telegram', {})
        self.lock = lock
        
        # 1. Telegram Token va Admins (.env birinchi navbatda)
        self.token = os.getenv("TELEGRAM_BOT_TOKEN") or self.cfg.get('bot_token')
        env_chat_ids = os.getenv("TELEGRAM_CHAT_ID")
        if env_chat_ids:
            self.admins = [c.strip() for c in env_chat_ids.split(',') if c.strip()]
        else:
            self.admins = [str(x).strip() for x in self.cfg.get('chat_id', [])]

        is_pa = "PYTHONANYWHERE_DOMAIN" in os.environ
        self.proxy = "http://proxy.server:3128" if is_pa else None
        self.base = f"https://api.telegram.org/bot{self.token}"
        
        # 2. AI Engine sozlamalari
        self.api_keys = config.get('gemini_ai', {}).get('api_keys', [])
        self.model_name = config.get('gemini_ai', {}).get('model', 'models/gemini-2.5-flash')
        
        # AI Engine o'zi .env dan yuklashni biladi
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

    async def send(self, text: str, cid=None, kb=None):
        if not cid:
            cids = self.admins
        else:
            cids = [cid]
        
        sess = await self.get_session()
        all_success = True
        for c in cids:
            sent_this = False
            
            # SMART CHUNKING
            text_str = str(text)
            chunks = []
            while len(text_str) > 4000:
                split_idx = text_str.rfind('\n\n', 0, 4000)
                if split_idx == -1:
                    split_idx = text_str.rfind('\n', 0, 4000)
                if split_idx == -1:
                    split_idx = 4000
                chunks.append(text_str[:split_idx])
                text_str = text_str[split_idx:].strip()
            if text_str:
                chunks.append(text_str)
                
            for i, chunk in enumerate(chunks):
                data = {'chat_id': c, 'text': chunk, 'parse_mode': 'HTML'}
                if kb and i == 0: data['reply_markup'] = kb
                
                print(f"[SENDING] To {c}...", flush=True)
                for attempt in range(3):
                    try:
                        async with sess.post(f"{self.base}/sendMessage", proxy=self.proxy, json=data, timeout=15) as r:
                            if r.status == 200:
                                print(f"[SENT] To {c}", flush=True)
                                sent_this = True
                                break
                            else:
                                txt = await r.text()
                                print(f"[SEND FAIL] Chunk {i+1}/{len(chunks)} To {c}. Status {r.status}: {txt}", flush=True)
                                if "can't parse entities" in txt:
                                    print(f"⚠️ HTML Parser Error on chunk: {chunk[:100]}...", flush=True)
                                if r.status in (502, 503, 504): await asyncio.sleep(1.5)
                                else: break
                    except Exception as e:
                        print(f"[SEND ERROR] Attempt {attempt+1}: {e}", flush=True)
                        await asyncio.sleep(1)
                if not sent_this: all_success = False
                await asyncio.sleep(0.3)
        return all_success

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
        success = True
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
                        success = await self.send(caption, cid=c, kb=kb)  # fallback
            except Exception as e:
                logger.warning(f"send_photo error: {e}")
                success = await self.send(caption, cid=c, kb=kb)
        return success

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
                import traceback
                error_trace = traceback.format_exc()
                try:
                    print(f"Polling Fatal Error:\n{error_trace}", flush=True)
                except: pass
                logger.error(f"Polling Fatal Error: {error_trace}")
                await asyncio.sleep(5)

    async def handle_update(self, u, bs, cfg_full, sess, off_file):
        """Yagona update qayta ishlash (TDD uchun ajratilgan)"""
        off = u['update_id']
        m = u.get('message', {})
        cb = u.get('callback_query', {})
        uid = str(cb.get('from', m.get('from', {})).get('id', ''))
        
        # Debug Loglar
        try:
            print(f"DEBUG: New Update ID {off}", flush=True)
            if cb: print(f"[CALLBACK] Data: {cb.get('data')} from {uid}", flush=True)
            if m:  print(f"[MESSAGE] Text: {m.get('text')} from {uid}", flush=True)
        except: pass
        
        is_admin = uid in self.admins
        current_state = self.user_states.get(uid)
        sym_list = cfg_full.get('symbols', ["XAU/USD", "BTC/USDT"])
        
        try:
            with open(off_file, 'w') as f: f.write(str(off))
        except: pass

        # ── Foydalanuvchini avtomatik ro'yxatga olish ────────────────────────
        if uid and uid != '':
            user_info = m.get('from', cb.get('from', {})) if cb else m.get('from', {})
            access_mode = self.db.get_setting("access_mode", "PUBLIC")
            default_st = "ACTIVE" if access_mode == "PUBLIC" else "PENDING"
            self.db.register_or_update_user(
                user_id=uid,
                username=user_info.get('username'),
                first_name=user_info.get('first_name'),
                last_name=user_info.get('last_name'),
                default_status=default_st
            )
            # Kirish nazorati (admin har doim o'tadi)
            if not is_admin:
                user_status = self.db.get_user_status(uid)
                is_denied = (user_status == 'BLOCKED') or (
                    access_mode == 'RESTRICTED' and user_status != 'ACTIVE'
                )
                if is_denied:
                    admin_link = self.db.get_setting("admin_link", "@Madaminjon01")
                    extra_text = self.db.get_setting("blocked_message_extra", "")
                    deny_msg = (
                        "⚠️ <b>Kechirasiz, sizda ushbu botdan foydalanish huquqi yo'q.</b>\n\n"
                        f"Tizimdan foydalanish va ruxsat olish uchun iltimos admin bilan bog'laning: {admin_link}"
                    )
                    if extra_text:
                        deny_msg += f"\n\n{extra_text}"
                    await self.send(deny_msg, cid=uid)
                    return off

        # Text to Callback Adapter (Sozlamalar menyusi uchun)
        t = str(m.get('text', ''))
        if not cb:
            text_to_cb = {
                "🪙 Instrumentlar": "sym_list",
                "⏱ Taymfreym": "tf_menu",
                "💰 Risk %": "risk_menu",
                "⚙️ Sifat": "qual_menu",
                "📊 Statistika (Win-rate)": "stat_winrate",
                "⚖️ Balans": "set_balance_menu",
                "📋 Bugungi Signallar": "today_signals",
                "📈 Oylik P&L": "monthly_pnl",
                "📜 Signal Tarixi": "signal_history",
                "🔔 Price Alert": "alert_list",
                "🌍 Vaqt Zonasi": "tz_menu",
                "🤖 AI Xulosa: 🟢 YOQ": "toggle_ai_review",
                "🤖 AI Xulosa: 🔴 O'CH": "toggle_ai_review",
                
                # SIFAT
                "🟢 Sifat: 30%": "setqual_30.0",
                "🟡 Sifat: 50%": "setqual_50.0",
                "🟠 Sifat: 75%": "setqual_75.0",
                "🔴 Sifat: 90%": "setqual_90.0",
                "🗑 Statistikani tozalash": "clear_stats_confirm",
                "✔️ Ha, o'chirish": "clear_stats_yes",
                
                # RISK
                "💰 Risk: 0.5%": "risk_0.5",
                "💰 Risk: 1.0%": "risk_1.0",
                "💰 Risk: 2.0%": "risk_2.0",
                "💰 Risk: 3.0%": "risk_3.0",
                "💰 Risk: 5.0%": "risk_5.0",
                
                # TAYMFREYM
                "⏱ Taymfreym: 5m": "tf_5m",
                "⏱ Taymfreym: 15m": "tf_15m",
                "⏱ Taymfreym: 1h": "tf_1h",
                "⏱ Taymfreym: 4h": "tf_4h",
                
                # INSTRUMENTLAR
                "➕ Qo'shish": "sym_add",
                "❌ O'chirish": "sym_rem",
                
                # SMC TRENER
                "📚 Mavzuli Darslar": "mentor_lessons",
                "🌐 Jonli Misollar": "mentor_live_examples",
                "❓ Erkin Savol-Javob": "mentor_qa",
                "🚪 Chiqish": "mentor_exit",

                # VAQT ZONASI
                "🇺🇿 UTC+5 (UZT)": "tz_set:5",
                "🇹🇷 UTC+3 (MSK)": "tz_set:3",
                "🇦🇪 UTC+2 (EET)": "tz_set:2",
                "🇦🇪 UTC+0 (GMT)": "tz_set:0",
                "🇦🇪 UTC+8 (SGT)": "tz_set:8",
                
                # ALERTLAR
                "➡️ Yangi Alert": "alert_add",
                "🗑 Hammasini O'chir": "alert_clear",
            }
            if t in text_to_cb:
                cb = {'id': 'fake_id', 'data': text_to_cb[t], 'from': {'id': uid}}
            elif t.startswith("❌ O'chirish: "):
                sym_name = t.replace("❌ O'chirish: ", "")
                cb = {'id': 'fake_id', 'data': f"sym_del:{sym_name}", 'from': {'id': uid}}
            elif t.startswith("🔍 Tahlil: "):
                parts = t.replace("🔍 Tahlil: ", "").split(" (")
                sym_name = parts[0]
                type_ai = parts[1].replace(")", "").lower()
                cb = {'id': 'fake_id', 'data': f"ai_{type_ai}:{sym_name}", 'from': {'id': uid}}
            elif t.startswith("🌍 TZ: "):
                tz = t.replace("🌍 TZ: ", "").split(" (")[0].replace("UTC+", "")
                cb = {'id': 'fake_id', 'data': f"tz_set:{tz}", 'from': {'id': uid}}

        # ── KEYBOARD LAYOUTS ────────────────────────────────────────────────
        ADMIN_KB = {'keyboard': [
            [{'text': "\U0001F4CA Texnik Tahlil"}, {'text': "\U0001F310 Fundamental"}],
            [{'text': "\U0001F468\u200D\U0001F3EB Jonli SMC Trener"}, {'text': "\U0001F4AC AI Chat Assistant"}],
            [{'text': "\u26A1 Scalping AI"}, {'text': "\U0001F4C8 Hisobot (Analytics)"}],
            [{'text': "\u2699\uFE0F Sozlamalar"}, {'text': "\u2696\uFE0F Risk Status"}],
            [{'text': "\U0001F4D6 Qo'llanma"}, {'text': "\U0001F9EA Test Signal"}],
            [{'text': "\U0001F6A8 PANIC CLOSE ALL"}]
        ], 'resize_keyboard': True}

        USER_KB = {'keyboard': [
            [{'text': "\U0001F4CA Texnik Tahlil"}, {'text': "\U0001F310 Fundamental"}],
            [{'text': "\U0001F468\u200D\u0001F3EB Jonli SMC Trener"}, {'text': "\U0001F4AC AI Chat Assistant"}],
            [{'text': "\U0001F4C8 Hisobot (Analytics)"}, {'text': "\U0001F4D6 Qo'llanma"}]
        ], 'resize_keyboard': True}

        KB = json.dumps(ADMIN_KB if is_admin else USER_KB)

        # Asosiy menyuga qaytish
        if t == "🔙 Asosiy Menyu":
            await self.send("🔙 Asosiy menyu", cid=uid, kb=KB)
            return off

        # ── CALLBACK QUERIES ─────────────────────────────────────────────────
        if cb:
            d = cb['data']
            # ⚡️ [CRITICAL] Darhol javob beramiz, shunda tugma loading holatidan chiqadi
            try: await sess.post(f"{self.base}/answerCallbackQuery", proxy=self.proxy, json={'callback_query_id': cb['id']}, timeout=5)
            except: pass

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

            # AI tahlil so'rovi (Inline tugmalar uchun)
            elif d.startswith("ai_") or d.startswith("analyze:"):
                prefix = "ai_" if d.startswith("ai_") else "analyze:"
                try:
                    data_parts = d.replace(prefix, "").split(":")
                    t_type = data_parts[0]
                    sym = data_parts[1] if len(data_parts) > 1 else "BTC/USDT"
                    
                    if t_type == "scalping" and not is_admin:
                        await sess.post(f"{self.base}/answerCallbackQuery", json={
                            'callback_query_id': cb['id'], 'text': "❌ Scalping faqat adminlar uchun.", 'show_alert': True})
                        return off
                        
                    with self.lock: bs['ai_requests'].append({
                        'type': t_type, 'symbol': sym, 
                        'chat_id': uid, 'text': f"{sym} uchun {t_type.upper()} tahlil ber.", 'image': None
                    })
                    await self.send(f"⏳ <i>{sym} uchun {t_type.upper()} tahlili tayyorlanmoqda...</i>", cid=uid)
                except Exception as e:
                    logger.error(f"AI Callback error: {e}")

            # ── SOZLAMALAR INLINE ──
            elif d == "sym_list":
                syms = cfg_full.get('symbols', [])
                text = "🪙 <b>Joriy instrumentlar:</b>\n\n" + "\n".join([f"• <code>{s}</code>" for s in syms])
                ikb = {'keyboard': [
                    [{'text': "➕ Qo'shish"}, {'text': "❌ O'chirish"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
                await self.send(text, cid=uid, kb=json.dumps(ikb))

            elif d == "sym_add" and is_admin:
                self.user_states[uid] = "wait_sym_add"
                ikb = {'keyboard': [[{'text': "🔙 Asosiy Menyu"}]], 'resize_keyboard': True}
                await self.send("➕ <b>Yangi instrument qo'shish:</b>\n\nNomini kiriting (masalan: <code>SOL/USDT</code>):", cid=uid, kb=json.dumps(ikb))

            elif d == "sym_rem" and is_admin:
                syms = cfg_full.get('symbols', [])
                # Har bir simvol uchun alohida tugma, matni: "❌ O'chirish: EUR/USD"
                kb_list = [[{'text': f"❌ O'chirish: {s}"}] for s in syms]
                kb_list.append([{'text': "🔙 Asosiy Menyu"}])
                ikb = {'keyboard': kb_list, 'resize_keyboard': True}
                await self.send("❌ <b>O'chirish uchun tanlang:</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("sym_del:") and is_admin:
                target = d.replace("sym_del:", "")
                if target in cfg_full.get('symbols', []):
                    cfg_full['symbols'].remove(target)
                    with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                    await self.send(f"✅ <code>{target}</code> ro'yxatdan o'chirildi.", cid=uid)

            elif d == "tf_menu":
                ikb = {'keyboard': [
                    [{'text': "⏱ Taymfreym: 5m"},  {'text': "⏱ Taymfreym: 15m"}],
                    [{'text': "⏱ Taymfreym: 1h"},  {'text': "⏱ Taymfreym: 4h"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
                await self.send("⏱ <b>Ishchi taymfreymni tanlang:</b>", cid=uid, kb=json.dumps(ikb))

            elif d.startswith("tf_") and d != "tf_menu" and is_admin:
                new_tf = d.replace("tf_", "")
                cfg_full['timeframe'] = new_tf
                with open('config/settings.yaml', 'w') as f: yaml.dump(cfg_full, f)
                await self.send(f"✅ Ishchi taymfreym <b>{new_tf}</b> ga o'zgartirildi.", cid=uid)

            elif d == "risk_menu":
                ikb = {'keyboard': [
                    [{'text': "💰 Risk: 0.5%"}, {'text': "💰 Risk: 1.0%"}],
                    [{'text': "💰 Risk: 2.0%"}, {'text': "💰 Risk: 3.0%"}],
                    [{'text': "💰 Risk: 5.0%"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
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
                ikb = {'keyboard': [
                    [{'text': "🟢 Sifat: 30%"}, {'text': "🟡 Sifat: 50%"}],
                    [{'text': "🟠 Sifat: 75%"}, {'text': "🔴 Sifat: 90%"}],
                    [{'text': "🗑 Statistikani tozalash"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
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
                ikb = {'keyboard': [
                    [{'text': "➕ Yangi Alert"}, {'text': "🗑 Hammasini O'chir"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
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
                ikb = {'keyboard': [
                    [{'text': "🇺🇿 UTC+5 (UZT)"}, {'text': "🇹🇷 UTC+3 (MSK)"}],
                    [{'text': "🇦🇪 UTC+2 (EET)"}, {'text': "🇦🇪 UTC+0 (GMT)"}],
                    [{'text': "🇦🇪 UTC+8 (SGT)"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
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
                ikb = {'keyboard': [[{'text': "🗑 Statistikani tozalash"}], [{'text': "🔙 Asosiy Menyu"}]], 'resize_keyboard': True}
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
                await self.send(msg, cid=uid, kb=json.dumps(ikb))

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
                current_state = None
                
                if uid not in self.onboarding_done:
                    self.onboarding_done.add(uid)
                    onboard = (
                        "🚀 <b>GEMINI SMC TITAN V27.2 ga xush kelibsiz!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "📖 <b>Qanday foydalanish kerak:</b>\n\n"
                        "➕ <b>1-qadam:</b> \"📊 Texnik Tahlil\" → instrument tanlang\n"
                        "➕ <b>2-qadam:</b> Signal avtomatik keladi (sifat ≥75%)\n"
                        "➕ <b>3-qadam:</b> Signal natijasida ✅ TP yoki ❌ SL bosing\n"
                        "➕ <b>4-qadam:</b> ❤️ Bot har soat ishlayotganini tasdiqlaydi\n\n"
                        "ℹ️ <b>Yordam:</b> \"📖 Qo'llanma\" tugmasini bosing"
                    )
                    await self.send(onboard, cid=uid)

                if is_admin:
                    with self.lock: bs['panic_request'] = False

                await self.send("<b>V27.2 A+ TITAN MASTER</b> botiga xush kelibsiz! 🚀", cid=uid, kb=KB)
                return off
            
            # ✅ Xavfsizlik filtri: Agar menyu tugmasi bosilsa, har qanday kutish holatini bekor qilish
            MENU_BUTTONS = [
                "📊 Texnik Tahlil", "🌐 Fundamental", "👨‍🏫 Jonli SMC Trener", 
                "💬 AI Chat Assistant", "⚡ Scalping AI", "📈 Hisobot", 
                "⚙️ Sozlamalar", "⚖️ Risk Status", "📖 Qo'llanma", 
                "🧪 Test Signal", "🚨 PANIC CLOSE ALL"
            ]
            if any(btn in t for btn in MENU_BUTTONS):
                self.user_states.pop(uid, None)
                current_state = None

            # FSM: Foydalanuvchi boshqaruvi — kutish holatlari (Admin only)
            USER_MGMT_STATES = {
                "wait_whitelist_uid", "wait_block_uid",
                "wait_admin_link", "wait_extra_text"
            }
            if t in ("/cancel", "bekor") and current_state in USER_MGMT_STATES:
                self.user_states.pop(uid, None)
                await self.send("🚫 Bekor qilindi.", cid=uid)
                return off

            if current_state == "wait_whitelist_uid" and is_admin and t:
                if t.strip().isdigit():
                    target_uid = t.strip()
                    existing = self.db.get_user_status(target_uid)
                    if existing is None:
                        self.db.register_or_update_user(target_uid, default_status="ACTIVE")
                    else:
                        self.db.update_user_status(target_uid, "ACTIVE")
                    self.user_states.pop(uid, None)
                    await self.send(
                        f"✅ <b>Foydalanuvchi ruxsatga olindi!</b>\n"
                        f"ID: <code>{target_uid}</code> → ACTIVE",
                        cid=uid
                    )
                else:
                    await self.send("❌ Faqat raqamli ID kiriting (masalan: <code>123456789</code>).", cid=uid)
                return off

            if current_state == "wait_block_uid" and is_admin and t:
                if t.strip().isdigit():
                    target_uid = t.strip()
                    existing = self.db.get_user_status(target_uid)
                    if existing is None:
                        self.db.register_or_update_user(target_uid, default_status="BLOCKED")
                    else:
                        self.db.update_user_status(target_uid, "BLOCKED")
                    self.user_states.pop(uid, None)
                    await self.send(
                        f"⛔ <b>Foydalanuvchi bloklandi!</b>\n"
                        f"ID: <code>{target_uid}</code> → BLOCKED",
                        cid=uid
                    )
                else:
                    await self.send("❌ Faqat raqamli ID kiriting (masalan: <code>123456789</code>).", cid=uid)
                return off

            if current_state == "wait_admin_link" and is_admin and t:
                new_link = t.strip()
                self.db.set_setting("admin_link", new_link)
                self.user_states.pop(uid, None)
                await self.send(
                    f"✅ <b>Admin havola yangilandi!</b>\n"
                    f"Yangi havola: <b>{new_link}</b>",
                    cid=uid
                )
                return off

            if current_state == "wait_extra_text" and is_admin and t:
                if t.strip().lower() in ("/clear", "clear"):
                    self.db.set_setting("blocked_message_extra", "")
                    await self.send("🗑 Qo'shimcha matn o'chirildi.", cid=uid)
                else:
                    self.db.set_setting("blocked_message_extra", t.strip())
                    await self.send(
                        f"✅ <b>Qo'shimcha matn saqlandi!</b>\n"
                        f"Matn: <i>{t.strip()}</i>",
                        cid=uid
                    )
                self.user_states.pop(uid, None)
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
                
                module_type = self.user_modules.get(uid, 'mentor_qa')
                detected_symbol = 'SMC'
                
                # Simbolni aniqlash uchun matnlar yig'indisi (Caption + Reply)
                search_text = user_text
                reply_to = m.get('reply_to_message', {})
                if reply_to:
                    search_text += " " + (reply_to.get('text', '') or reply_to.get('caption', '') or "")
                
                if search_text:
                    _SYMBOL_HINTS = {
                        'gold': 'XAU/USD', 'xau/usd': 'XAU/USD', 'xau': 'XAU/USD', 'oltin': 'XAU/USD', 'xausd': 'XAU/USD',
                        'silver': 'XAG/USD', 'xag/usd': 'XAG/USD', 'xag': 'XAG/USD', 'kumush': 'XAG/USD',
                        'btc': 'BTC/USDT', 'btc/usdt': 'BTC/USDT', 'bitcoin': 'BTC/USDT',
                        'eth': 'ETH/USDT', 'eth/usdt': 'ETH/USDT', 'ethereum': 'ETH/USDT', 'efir': 'ETH/USDT',
                        'eur': 'EUR/USD', 'eur/usd': 'EUR/USD', 'gbp': 'GBP/USD', 'gbp/usd': 'GBP/USD',
                        'dxy': 'DXY', 'dollar': 'DXY',
                        'oil': 'OIL/USD', 'neft': 'OIL/USD',
                        'nasdaq': 'NASDAQ', 'sp500': 'S&P500',
                    }
                    _txt_lower = search_text.lower()
                    for hint, sym_name in _SYMBOL_HINTS.items():
                        if hint in _txt_lower:
                            detected_symbol = sym_name
                            break
                
                with self.lock: bs['ai_requests'].append({
                    'type': module_type,
                    'symbol': detected_symbol, 'chat_id': uid,
                    'text': user_text, 'image': img_data
                })
                await self.send("🧠 [AI tahlil qilmoqda...]", cid=uid)
                return off

            # ── ASOSIY MENYU TUGMALARI ───────────────────────────────────────

            if "Sozlamalar" in t and is_admin:
                ai_enabled = bs.get('settings', {}).get('ai_review_enabled', True)
                ai_btn = "🤖 AI Xulosa: 🟢 YOQ" if ai_enabled else "🤖 AI Xulosa: 🔴 O'CH"
                ikb = {'keyboard': [
                    [{'text': "🪙 Instrumentlar"}, {'text': "⏱ Taymfreym"}],
                    [{'text': "💰 Risk %"},         {'text': "⚙️ Sifat"}],
                    [{'text': "📊 Statistika (Win-rate)"}, {'text': "⚖️ Balans"}],
                    [{'text': "📋 Bugungi Signallar"}, {'text': "📈 Oylik P&L"}],
                    [{'text': "📜 Signal Tarixi"},   {'text': "🔔 Price Alert"}],
                    [{'text': "🌍 Vaqt Zonasi"},     {'text': ai_btn}],
                    [{'text': "👤 A'zolarni Boshqarish"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
                await self.send("⚙️ <b>Bot Sozlamalari:</b>", cid=uid, kb=json.dumps(ikb))

            elif "Sozlamalarga Qaytish" in t and is_admin:
                # A'zolar menyusidan sozlamalarga qaytish
                ai_enabled = bs.get('settings', {}).get('ai_review_enabled', True)
                ai_btn = "🤖 AI Xulosa: 🟢 YOQ" if ai_enabled else "🤖 AI Xulosa: 🔴 O'CH"
                ikb = {'keyboard': [
                    [{'text': "🪙 Instrumentlar"}, {'text': "⏱ Taymfreym"}],
                    [{'text': "💰 Risk %"},         {'text': "⚖️ Sifat"}],
                    [{'text': "📊 Statistika (Win-rate)"}, {'text': "⚖️ Balans"}],
                    [{'text': "📋 Bugungi Signallar"}, {'text': "📈 Oylik P&L"}],
                    [{'text': "📜 Signal Tarixi"},   {'text': "🔔 Price Alert"}],
                    [{'text': "🌍 Vaqt Zonasi"},     {'text': ai_btn}],
                    [{'text': "👤 A'zolarni Boshqarish"}],
                    [{'text': "🔙 Asosiy Menyu"}]
                ], 'resize_keyboard': True}
                await self.send("⚙️ <b>Bot Sozlamalari:</b>", cid=uid, kb=json.dumps(ikb))

            elif "zolarni Boshqarish" in t and is_admin:
                # 👤 A'zolarni Boshqarish submenyusi
                cur_mode = self.db.get_setting("access_mode", "PUBLIC")
                mode_emoji = "🔓" if cur_mode == "PUBLIC" else "🔒"
                ikb = {'keyboard': [
                    [{'text': "👥 A'zolar Ro'yxati"}],
                    [{'text': "🔓 Hammaga Ochiq (PUBLIC)"}, {'text': "🔒 Tanlanganlarga (RESTRICTED)"}],
                    [{'text': "➕ Ruxsat Berish"}, {'text': "⛔ Bloklash"}],
                    [{'text': "🔗 Havolani O'zgartirish"}, {'text': "✍️ Matnni Tahrirlash"}],
                    [{'text': "🔙 Sozlamalarga Qaytish"}]
                ], 'resize_keyboard': True}
                await self.send(
                    f"👤 <b>A'zolarni Boshqarish</b>\n"
                    f"Joriy kirish rejimi: {mode_emoji} <b>{cur_mode}</b>\n\n"
                    f"Quyidagilardan birini tanlang:",
                    cid=uid, kb=json.dumps(ikb)
                )

            elif "zolar Ro" in t and is_admin:
                users = self.db.get_all_users()
                if not users:
                    await self.send("👥 Hozircha ro'yxatda hech kim yo'q.", cid=uid)
                else:
                    status_emoji = {'ACTIVE': '✅', 'BLOCKED': '⛔', 'PENDING': '⏳'}
                    lines = ["👥 <b>Foydalanuvchilar Ro'yxati</b>\n"]
                    for i, u_rec in enumerate(users[:40], 1):  # Max 40 ta
                        em = status_emoji.get(u_rec['status'], '❓')
                        uname = f"@{u_rec['username']}" if u_rec['username'] else u_rec['first_name'] or "Noma'lum"
                        lines.append(
                            f"{i}. {em} <code>{u_rec['user_id']}</code> — {uname} [{u_rec['status']}]"
                        )
                    lines.append(f"\n<i>Jami: {len(users)} ta foydalanuvchi</i>")
                    await self.send("\n".join(lines), cid=uid)

            elif "Hammaga Ochiq" in t and is_admin:
                self.db.set_setting("access_mode", "PUBLIC")
                await self.send(
                    "🔓 <b>Hammaga Ochiq (PUBLIC)</b> rejimi faollashtirildi.\n"
                    "Yangi foydalanuvchilar avtomatik ACTIVE bo'ladi.",
                    cid=uid
                )

            elif "Tanlanganlarga" in t and is_admin:
                self.db.set_setting("access_mode", "RESTRICTED")
                await self.send(
                    "🔒 <b>Tanlanganlarga Ochiq (RESTRICTED)</b> rejimi faollashtirildi.\n"
                    "Faqat siz ruxsat bergan foydalanuvchilar kira oladi.",
                    cid=uid
                )

            elif "Ruxsat Berish" in t and is_admin:
                self.user_states[uid] = "wait_whitelist_uid"
                await self.send(
                    "➕ Ruxsat bermoqchi bo'lgan foydalanuvchining <b>ID raqamini</b> yuboring:\n"
                    "<i>(Bekor qilish uchun /cancel yozing)</i>",
                    cid=uid
                )

            elif "⛔ Bloklash" in t and is_admin:
                self.user_states[uid] = "wait_block_uid"
                await self.send(
                    "⛔ Bloklash kerak bo'lgan foydalanuvchining <b>ID raqamini</b> yuboring:\n"
                    "<i>(Bekor qilish uchun /cancel yozing)</i>",
                    cid=uid
                )

            elif "Havolani O'zgartirish" in t and is_admin:
                cur_link = self.db.get_setting("admin_link", "@Madaminjon01")
                self.user_states[uid] = "wait_admin_link"
                await self.send(
                    f"🔗 Joriy havola: <b>{cur_link}</b>\n\n"
                    f"Yangi admin havolasini yuboring (masalan: @YangiAdmin yoki t.me/yangi):\n"
                    f"<i>(Bekor qilish uchun /cancel yozing)</i>",
                    cid=uid
                )

            elif "Matnni Tahrirlash" in t and is_admin:
                cur_extra = self.db.get_setting("blocked_message_extra", "")
                self.user_states[uid] = "wait_extra_text"
                display = f"\"<i>{cur_extra}</i>\"" if cur_extra else "<i>(bo'sh)</i>"
                await self.send(
                    f"✍️ Joriy qo'shimcha matn: {display}\n\n"
                    f"Yangi qo'shimcha matn yuboring (o'chirish uchun /clear yozing):\n"
                    f"<i>(Bekor qilish uchun /cancel yozing)</i>",
                    cid=uid
                )

            elif "Jonli SMC Trener" in t:
                self.user_states[uid] = "choosing_module"
                ikb = {'keyboard': [
                    [{'text': "📚 Mavzuli Darslar"}, {'text': "🌐 Jonli Misollar"}],
                    [{'text': "❓ Erkin Savol-Javob"}, {'text': "🚪 Chiqish"}]
                ], 'resize_keyboard': True}
                await self.send("👨‍🏫 <b>Jonli SMC Trener</b> rejimi:\n\nQaysi modulni tanlaysiz?", cid=uid, kb=json.dumps(ikb))

            elif any(x in t for x in ["Texnik Tahlil", "Fundamental", "Scalping"]):
                if "Scalp" in t and not is_admin:
                    await self.send("❌ Scalping AI faqat adminlar uchun.", cid=uid)
                    return off
                type_ai = 'fundamental' if 'Fund' in t else ('scalping' if 'Scalp' in t else 'technical')
                
                # Fundamental uchun chat sessiyasini ochamiz (fayl yuklash uchun)
                if type_ai == 'fundamental':
                    self.user_states[uid] = "in_session"
                    self.user_modules[uid] = "fundamental"
                    await self.send("🌐 <b>Fundamental Tahlil</b> faollashdi.\n\nSavolingizni yozing yoki fayl/rasm yuklang:", cid=uid)
                    return off

                ikb = {'keyboard': [[{'text': f"🔍 Tahlil: {s} ({type_ai.upper()})"} ] for s in sym_list], 'resize_keyboard': True}
                ikb['keyboard'].append([{'text': "🔙 Asosiy Menyu"}])
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
                from datetime import datetime, timezone, timedelta
                uzt = datetime.now(timezone.utc) + timedelta(hours=5)
                # Haqiqiy signal formatini simulyatsiya qilish
                msg  = f"🚀 <b>YANGI SIGNAL: EUR/USD (TEST)</b>\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"🔔 Signal: <b>🟢 BUY (LONG)</b>\n"
                msg += f"💎 Sifat: <code>95.0%</code>\n\n"
                msg += f"📥 1-Kirish: <code>1.0500</code>\n"
                msg += f"📥 2-Kirish: <code>1.0492</code>\n"
                msg += f"🛡 Stop-Loss: <code>1.0480</code>\n\n"
                msg += f"🎯 Maqsadlar:\n"
                msg += f"   1. TP1: <code>1.0520</code>\n"
                msg += f"   2. TP2: <code>1.0560</code>\n"
                msg += f"   3. TP3: <code>1.0600</code>\n\n"
                msg += f"🧠 <b>Asos:</b> SMC BOS UP + FVG + Discount Zone\n"
                msg += f"🤖 <b>AI Xulosasi:</b> Signal trend yo'nalishida va kuchli talab zonasidan qaytmoqda.\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"🕐 <b>UZT:</b> {uzt.strftime('%H:%M')} | 🏛 <b>Terminal:</b> 12:00\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"💰 <b>Position Sizing:</b>\n"
                msg += f"   ├ Risk: $100.0 (2.0%)\n"
                msg += f"   ├ SL masofa: 20 pip\n"
                msg += f"   ├ Hajm: 0.50 Lot\n"
                msg += f"   └ R:R → TP1: 1:1.0 | TP2: 1:3.0\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"⚡ Titan V27.2 Master"
                
                ikb = {'inline_keyboard': [[
                    {'text': "✅ TP urdi", 'callback_data': "sig_tp:test:EUR/USD"},
                    {'text': "❌ SL urdi", 'callback_data': "sig_sl:test:EUR/USD"},
                    {'text': "⏭ O'tkazdim", 'callback_data': "sig_skip:test:EUR/USD"}
                ]]}
                await self.send(msg, cid=uid, kb=json.dumps(ikb))

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

            elif "🔍 Tahlil:" in t:
                # Format: "🔍 Tahlil: ETH/USDT (TECHNICAL)"
                try:
                    parts = t.split(":")
                    if len(parts) > 1:
                        sub_parts = parts[1].strip().split("(")
                        sym = sub_parts[0].strip()
                        analysis_type = sub_parts[1].replace(")", "").lower().strip() if len(sub_parts) > 1 else "technical"
                        
                        with self.lock: bs['ai_requests'].append({
                            'type': analysis_type, 'symbol': sym,
                            'chat_id': uid, 'text': f"{sym} uchun {analysis_type.upper()} tahlil ber.", 'image': None
                        })
                        await self.send(f"⏳ <b>{sym}</b> uchun {analysis_type.upper()} tahlili tayyorlanmoqda...", cid=uid)
                        return off
                except Exception as e:
                    logger.error(f"Tahlil tugmasi xatosi: {e}")

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

                # Simbolni matndan aniqlash
                detected_symbol = 'KB'
                search_text = user_text
                reply_to = m.get('reply_to_message', {})
                if reply_to:
                    search_text += " " + (reply_to.get('text', '') or reply_to.get('caption', '') or "")
                
                if search_text:
                    _SYMBOL_HINTS = {
                        'gold': 'XAU/USD', 'xau/usd': 'XAU/USD', 'xau': 'XAU/USD', 'oltin': 'XAU/USD', 'xausd': 'XAU/USD',
                        'silver': 'XAG/USD', 'xag/usd': 'XAG/USD', 'xag': 'XAG/USD', 'kumush': 'XAG/USD',
                        'btc': 'BTC/USDT', 'btc/usdt': 'BTC/USDT', 'bitcoin': 'BTC/USDT',
                        'eth': 'ETH/USDT', 'eth/usdt': 'ETH/USDT', 'ethereum': 'ETH/USDT', 'efir': 'ETH/USDT',
                        'eur': 'EUR/USD', 'eur/usd': 'EUR/USD', 'gbp': 'GBP/USD', 'gbp/usd': 'GBP/USD',
                        'dxy': 'DXY', 'dollar': 'DXY',
                        'oil': 'OIL/USD', 'neft': 'OIL/USD',
                        'nasdaq': 'NASDAQ', 'sp500': 'S&P500',
                    }
                    _txt_lower = search_text.lower()
                    for hint, sym_name in _SYMBOL_HINTS.items():
                        if hint in _txt_lower:
                            detected_symbol = sym_name
                            break

                with self.lock: bs['ai_requests'].append({
                    'type': 'chat', 'symbol': detected_symbol,
                    'chat_id': uid, 'text': user_text, 'image': img_data
                })
                await self.send("⏳ Tahlil boshlandi...", cid=uid)

        return off
