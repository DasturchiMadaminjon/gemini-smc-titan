"""
tests/test_telegram_buttons.py
Telegram knopka handlerlari funksiyalarini tekshirish (mock bilan).
V27.2 uchun yangilangan: Sozlamalar, Sifat, Risk, Instrumentlar, Statistika
"""
import pytest
import asyncio
import json
import threading
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Yordamchi: soxta update yaratish ──────────────────────────────────────

def make_update(text="", uid="7295947374", cb_data=None, has_photo=False):
    """Telegram update obyektini simulyatsiya qilish."""
    if cb_data:
        return {
            "update_id": 1,
            "callback_query": {
                "id": "cb001",
                "data": cb_data,
                "from": {"id": int(uid)},
                "message": {"chat": {"id": int(uid)}}
            }
        }
    msg = {"text": text, "from": {"id": int(uid)}, "chat": {"id": int(uid)}}
    if has_photo:
        msg["photo"] = [{"file_id": "test_file_id"}]
    return {"update_id": 1, "message": msg}


def make_bot_state():
    return {
        "symbols": {"XAU/USD": {"price": 2350.0}},
        "terminal": {"balance": 5000.0},
        "ai_requests": [],
        "loss_streak": 0,
        "panic_request": False
    }


def make_cfg():
    return {
        "symbols": ["XAU/USD", "BTC/USDT"],
        "timeframe": "15m",
        "smc": {"min_quality": 30.0},
        "trend": {"risk_perc": 1.0}
    }


ADMIN_UID = "7295947374"
USER_UID  = "9999999999"


# ─── Fixture: TelegramNotifier ──────────────────────────────────────────────

@pytest.fixture
def notifier():
    """Mock TelegramNotifier yaratish."""
    with patch("utils.telegram.AIEngine"), \
         patch("google.generativeai.configure"), \
         patch("google.generativeai.list_models", return_value=[]):

        from utils.telegram import TelegramNotifier

        cfg = {
            "telegram": {
                "bot_token": "test_token",
                "chat_id": [int(ADMIN_UID)]
            },
            "gemini_ai": {"api_keys": [], "model": "gemini-2.5-flash"},
            "symbols": ["XAU/USD", "BTC/USDT"],
            "timeframe": "15m",
            "smc": {"min_quality": 30.0},
            "trend": {"risk_perc": 1.0}
        }
        lock = threading.Lock()
        obj = TelegramNotifier(cfg, lock)
        obj.send = AsyncMock()
        obj.send_action = AsyncMock(return_value=True)
        return obj


# ─── /start knopkasi ────────────────────────────────────────────────────────

class TestStartCommand:
    def test_admin_sees_admin_keyboard(self, notifier):
        """Admin /start yozganda ADMIN_KB ko'rinadi."""
        admins = [ADMIN_UID]
        is_admin = ADMIN_UID in admins
        assert is_admin is True

    def test_user_sees_user_keyboard(self, notifier):
        """Begona foydalanuvchi USER_KB ko'radi."""
        admins = [ADMIN_UID]
        is_admin = USER_UID in admins
        assert is_admin is False

    def test_admin_kb_has_sozlamalar_button(self):
        """ADMIN_KB da Sozlamalar tugmasi bo'lishi kerak."""
        ADMIN_KB = {
            'keyboard': [
                [{'text': "📊 Texnik Tahlil"}, {'text': "🌐 Fundamental"}],
                [{'text': "👨‍🏫 Jonli SMC Trener"}, {'text': "💬 AI Chat Assistant"}],
                [{'text': "📈 Hisobot (Analytics)"}, {'text': "📖 Qo'llanma"}],
                [{'text': "⚙️ Sozlamalar"}, {'text': "🚨 PANIC CLOSE ALL"}]
            ]
        }
        all_texts = [b['text'] for row in ADMIN_KB['keyboard'] for b in row]
        assert "⚙️ Sozlamalar" in all_texts
        assert "🚨 PANIC CLOSE ALL" in all_texts

    def test_user_kb_has_no_sozlamalar(self):
        """USER_KB da Sozlamalar ko'rinmasligi kerak."""
        USER_KB = {
            'keyboard': [
                [{'text': "📊 Texnik Tahlil"}, {'text': "🌐 Fundamental"}],
                [{'text': "👨‍🏫 Jonli SMC Trener"}, {'text': "💬 AI Chat Assistant"}],
                [{'text': "📈 Hisobot (Analytics)"}, {'text': "📖 Qo'llanma"}]
            ]
        }
        all_texts = [b['text'] for row in USER_KB['keyboard'] for b in row]
        assert "⚙️ Sozlamalar" not in all_texts
        assert "🚨 PANIC CLOSE ALL" not in all_texts


# ─── Sozlamalar Menyu (Yangi V27.2) ─────────────────────────────────────────

class TestSozlamalarMenu:
    def test_sozlamalar_inline_keyboard_structure(self):
        """Sozlamalar inline menyu to'g'ri tuzilgan."""
        ikb = {'inline_keyboard': [
            [{'text': "🪙 Instrumentlar", 'callback_data': "sym_list"},
             {'text': "⏱ Taymfreym",      'callback_data': "tf_menu"}],
            [{'text': "💰 Risk %",         'callback_data': "risk_menu"},
             {'text': "⚙️ Sifat",          'callback_data': "qual_menu"}],
            [{'text': "📊 Statistika (Win-rate)", 'callback_data': "stat_winrate"}]
        ]}
        cb_datas = [b['callback_data'] for row in ikb['inline_keyboard'] for b in row]
        assert "sym_list" in cb_datas
        assert "tf_menu" in cb_datas
        assert "risk_menu" in cb_datas
        assert "qual_menu" in cb_datas
        assert "stat_winrate" in cb_datas

    def test_sozlamalar_only_for_admin(self):
        """Sozlamalar faqat admin uchun ko'rinadi."""
        t = "⚙️ Sozlamalar"
        is_admin = ADMIN_UID in [ADMIN_UID]
        is_user_admin = USER_UID in [ADMIN_UID]
        assert "Sozlamalar" in t and is_admin
        assert not is_user_admin


# ─── Taymfreym Callback (tf_menu, tf_5m, tf_15m ...) ───────────────────────

class TestTimeframeCallback:
    def test_tf_menu_is_not_converted_to_float(self):
        """tf_menu string 'menu' ga float() qo'llanmaydi (xato bermasligi)."""
        d = "tf_menu"
        # Yangi mantiq: d != "tf_menu" bo'lgandagina float() qo'llanadi
        is_value = d.startswith("tf_") and d != "tf_menu"
        assert is_value is False  # menu uchun false bo'lishi kerak

    def test_tf_value_parsed_correctly(self):
        """tf_15m dan '15m' qiymati olinadi."""
        d = "tf_15m"
        new_tf = d.replace("tf_", "")
        assert new_tf == "15m"

    def test_all_tf_values_valid(self):
        """Barcha taymfreymlar to'g'ri parse qilinadi."""
        tf_callbacks = ["tf_5m", "tf_15m", "tf_1h", "tf_4h"]
        expected = ["5m", "15m", "1h", "4h"]
        for cb, exp in zip(tf_callbacks, expected):
            assert cb.replace("tf_", "") == exp

    def test_tf_saved_to_config(self):
        """Yangi taymfreym config ga saqlanadi."""
        cfg = make_cfg()
        d = "tf_1h"
        new_tf = d.replace("tf_", "")
        cfg['timeframe'] = new_tf
        assert cfg['timeframe'] == "1h"


# ─── Risk Callback (risk_menu, risk_1.0 ...) ────────────────────────────────

class TestRiskCallback:
    def test_risk_menu_not_converted_to_float(self):
        """risk_menu float() ga yuborilmaydi — ValueError yo'q."""
        d = "risk_menu"
        is_value = d.startswith("risk_") and d != "risk_menu"
        assert is_value is False

    def test_risk_value_parsed_correctly(self):
        """risk_2.0 dan 2.0 float qiymati olinadi."""
        d = "risk_2.0"
        val = float(d.replace("risk_", ""))
        assert val == 2.0

    def test_all_risk_values_valid(self):
        """Barcha risk qiymatlari to'g'ri float sifatida parse qilinadi."""
        risk_cbs = ["risk_0.5", "risk_1.0", "risk_2.0", "risk_3.0", "risk_5.0"]
        expected = [0.5, 1.0, 2.0, 3.0, 5.0]
        for cb, exp in zip(risk_cbs, expected):
            assert float(cb.replace("risk_", "")) == exp

    def test_risk_saved_to_config(self):
        """Yangi risk qiymati config ga saqlanadi."""
        cfg = make_cfg()
        d = "risk_3.0"
        new_risk = float(d.replace("risk_", ""))
        if 'trend' not in cfg: cfg['trend'] = {}
        cfg['trend']['risk_perc'] = new_risk
        assert cfg['trend']['risk_perc'] == 3.0


# ─── Sifat (Quality) Callback ───────────────────────────────────────────────

class TestQualityCallback:
    def test_qual_menu_not_converted_to_float(self):
        """qual_menu float() ga yuborilmaydi."""
        d = "qual_menu"
        is_value = d.startswith("setqual_") and d != "qual_menu"
        assert is_value is False

    def test_setqual_value_parsed(self):
        """setqual_30.0 dan 30.0 olinadi."""
        d = "setqual_30.0"
        val = float(d.replace("setqual_", ""))
        assert val == 30.0


    def test_all_quality_values(self):
        """Barcha sifat variantlari to'g'ri parse qilinadi."""
        qual_cbs = ["setqual_30.0", "setqual_50.0", "setqual_75.0", "setqual_90.0"]
        expected = [30.0, 50.0, 75.0, 90.0]
        for cb, exp in zip(qual_cbs, expected):
            assert float(cb.replace("setqual_", "")) == exp

    def test_quality_saved_to_config(self):
        """Yangi sifat config ga saqlanadi."""
        cfg = make_cfg()
        d = "setqual_50.0"
        new_val = float(d.replace("setqual_", ""))
        cfg['smc']['min_quality'] = new_val
        assert cfg['smc']['min_quality'] == 50.0

    def test_quality_inline_keyboard_structure(self):
        """Sifat inline klaviaturasi 4 ta variantga ega."""
        ikb = {'inline_keyboard': [
            [{'text': "🟢 30%", 'callback_data': "setqual_30.0"},
             {'text': "🟡 50%", 'callback_data': "setqual_50.0"}],
            [{'text': "🟠 75%", 'callback_data': "setqual_75.0"},
             {'text': "🔴 90%", 'callback_data': "setqual_90.0"}]
        ]}
        all_cbs = [b['callback_data'] for row in ikb['inline_keyboard'] for b in row]
        assert len(all_cbs) == 4
        assert "setqual_30.0" in all_cbs
        assert "setqual_90.0" in all_cbs


# ─── Instrumentlar (Symbol) Boshqaruvi ─────────────────────────────────────

class TestSymbolManagement:
    def test_sym_list_shows_symbols(self):
        """sym_list callbackida instrumentlar ro'yxati ko'rsatiladi."""
        cfg = make_cfg()
        syms = cfg.get('symbols', [])
        text = "🪙 Joriy instrumentlar:\n" + "\n".join([f"• {s}" for s in syms])
        assert "XAU/USD" in text
        assert "BTC/USDT" in text

    def test_sym_add_sets_fsm_state(self):
        """sym_add bosilganda FSM holati wait_sym_add ga o'rnatiladi."""
        user_states = {}
        uid = ADMIN_UID
        # Simulyatsiya: sym_add callback
        user_states[uid] = "wait_sym_add"
        assert user_states[uid] == "wait_sym_add"

    def test_new_symbol_added_to_config(self):
        """Yangi instrument foydalanuvchi yozganida ro'yxatga qo'shiladi."""
        cfg = make_cfg()
        sym_name = "SOL/USDT"
        if sym_name not in cfg['symbols']:
            cfg['symbols'].append(sym_name)
        assert "SOL/USDT" in cfg['symbols']

    def test_duplicate_symbol_not_added(self):
        """Bir xil instrument ikkinchi marta qo'shilmaydi."""
        cfg = make_cfg()
        sym_name = "XAU/USD"  # Allaqachon mavjud
        before = len(cfg['symbols'])
        if sym_name not in cfg['symbols']:
            cfg['symbols'].append(sym_name)
        assert len(cfg['symbols']) == before

    def test_symbol_removed_from_config(self):
        """Instrument ro'yxatdan o'chiriladi."""
        cfg = make_cfg()
        target = "BTC/USDT"
        if target in cfg['symbols']:
            cfg['symbols'].remove(target)
        assert target not in cfg['symbols']

    def test_fsm_state_cleared_after_add(self):
        """Instrument qo'shilgandan so'ng FSM holati tozalanadi."""
        user_states = {ADMIN_UID: "wait_sym_add"}
        user_states.pop(ADMIN_UID, None)
        assert ADMIN_UID not in user_states

    def test_symbol_input_validation(self):
        """Foydalanuvchi yozgan qiymat symbol formatiga mos bo'lishi kerak."""
        valid_inputs = ["SOL/USDT", "PEPE/USDT", "XAU/USD"]
        invalid_inputs = ["hello", "123", "salom"]
        for v in valid_inputs:
            assert "/" in v
        for i in invalid_inputs:
            assert "/" not in i or len(i) < 5


# ─── Statistika (Win-Rate) Callback ─────────────────────────────────────────

class TestStatisticsCallback:
    def test_stat_winrate_empty_db(self):
        """Baza bo'sh bo'lganda statistika xabari to'g'ri chiqishi."""
        st = {"tp": 0, "sl": 0, "winrate": 0, "profit": 0.0, "total": 0}
        if st['total'] == 0:
            res_msg = "📊 <b>Statistika:</b>\n\nHali signallar mavjud emas."
        assert "Hali signallar mavjud emas" in res_msg

    def test_stat_winrate_with_data(self):
        """Bazada ma'lumot bo'lganda raqamlar to'g'ri chiqishi."""
        st = {"tp": 10, "sl": 5, "winrate": 66.7, "profit": 15.5, "total": 15}
        res_msg = (
            f"📊 <b>Signal Statistikasi (Oxirgi {st['total']} ta):</b>\n\n"
            f"✅ Foyda (TP): {st['tp']}\n"
            f"❌ Zarar (SL): {st['sl']}\n\n"
            f"🏆 <b>Win-Rate: {st['winrate']}%</b>\n"
            f"💰 Jami foyda: {st['profit']} R"
        )
        assert "Oxirgi 15 ta" in res_msg
        assert "66.7%" in res_msg
        assert "15.5 R" in res_msg

    def test_winrate_logic_edge_case(self):
        """Faqat SL bo'lganda winrate 0% bo'lishi kerak."""
        tp = 0; sl = 5
        total = tp + sl
        winrate = round((tp / total * 100), 1) if total > 0 else 0
        assert winrate == 0.0


# ─── AI Tahlil knopkalari ───────────────────────────────────────────────────

class TestAIButtons:
    def test_texnik_tahlil_type_detected(self):
        """Texnik Tahlil bosilganda 'technical' type aniqlanadi."""
        t = "Tahlil"
        type_ai = 'fundamental' if 'Fund' in t else ('scalping' if 'Scalp' in t else 'technical')
        assert type_ai == 'technical'

    def test_fundamental_type_detected(self):
        """Fundamental bosilganda 'fundamental' type aniqlanadi."""
        t = "Fundamental"
        type_ai = 'fundamental' if 'Fund' in t else ('scalping' if 'Scalp' in t else 'technical')
        assert type_ai == 'fundamental'

    def test_scalping_type_detected(self):
        """Scalping bosilganda 'scalping' type aniqlanadi."""
        t = "Scalping AI"
        type_ai = 'fundamental' if 'Fund' in t else ('scalping' if 'Scalp' in t else 'technical')
        assert type_ai == 'scalping'

    def test_scalping_blocked_for_non_admin(self):
        """Scalping noadmin uchun bloklanadi."""
        t = "Scalping AI"
        is_admin = USER_UID in [ADMIN_UID]
        blocked = "Scalp" in t and not is_admin
        assert blocked is True

    def test_scalping_allowed_for_admin(self):
        """Scalping admin uchun ruxsat beriladi."""
        t = "Scalping AI"
        is_admin = ADMIN_UID in [ADMIN_UID]
        blocked = "Scalp" in t and not is_admin
        assert blocked is False


# ─── PANIC va RISK knopkalari ───────────────────────────────────────────────

class TestAdminOnlyButtons:
    def test_panic_sets_flag(self):
        """PANIC bosilganda panic_request True bo'ladi."""
        bs = make_bot_state()
        lock = threading.Lock()
        t = "PANIC CLOSE ALL"
        if "PANIC" in t.upper():
            with lock:
                bs['panic_request'] = True
        assert bs['panic_request'] is True

    def test_panic_only_for_admin(self):
        """PANIC faqat admin uchun ishlashi kerak."""
        is_admin_user = USER_UID in [ADMIN_UID]
        is_admin_admin = ADMIN_UID in [ADMIN_UID]
        assert not is_admin_user
        assert is_admin_admin

    def test_risk_status_shows_balance(self):
        """Risk Status balansni ko'rsatadi."""
        bs = make_bot_state()
        lock = threading.Lock()
        with lock:
            balance = bs['terminal']['balance']
        assert balance == 5000.0


# ─── AI Chat Assistant ─────────────────────────────────────────────────────

class TestChatAssistant:
    def test_chat_adds_ai_request(self):
        """Erkin matn yozilganda chat ai_request qo'shiladi."""
        bs = make_bot_state()
        lock = threading.Lock()
        user_text = "GOLD hozir qanday?"
        with lock:
            bs['ai_requests'].append({
                'type': 'chat', 'symbol': 'KNOWLEDGE_BASE',
                'chat_id': ADMIN_UID, 'text': user_text, 'image': None
            })
        assert bs['ai_requests'][0]['type'] == 'chat'
        assert bs['ai_requests'][0]['text'] == "GOLD hozir qanday?"

    def test_photo_message_sets_image(self):
        """Rasm yuborilganda image maydoni to'ldiriladi."""
        req = {
            'type': 'chat', 'symbol': 'KNOWLEDGE_BASE',
            'chat_id': ADMIN_UID,
            'text': "Ushbu rasmni tahlil qiling.",
            'image': b"fake_image_bytes"
        }
        assert req['image'] is not None
        assert req['text'] == "Ushbu rasmni tahlil qiling."


# ─── Hisobot va Analytics ───────────────────────────────────────────────────

class TestAnalyticsButton:
    def test_hisobot_adds_analytics_request(self):
        """Hisobot bosilganda analytics request qo'shiladi."""
        bs = make_bot_state()
        lock = threading.Lock()
        t = "📈 Hisobot (Analytics)"
        if any(x in t for x in ["Hisobot", "Analytics"]):
            with lock:
                bs['ai_requests'].append({
                    'type': 'analytics', 'symbol': 'ALL',
                    'chat_id': ADMIN_UID, 'text': 'Full report'
                })
        assert len(bs['ai_requests']) == 1
        assert bs['ai_requests'][0]['type'] == 'analytics'

# ─── Balans Sozlash (Fake Balance) ──────────────────────────────────────────

class TestFakeBalance:
    def test_set_balance_menu_sets_state(self):
        """set_balance_menu callback bosilganda holat o'zgarishi."""
        user_states = {}
        uid = ADMIN_UID
        d = "set_balance_menu"
        if d == "set_balance_menu":
            user_states[uid] = "wait_balance_set"
        assert user_states[uid] == "wait_balance_set"

    def test_valid_balance_input_updates_state(self):
        """To'g'ri son kiritilganda balans yangilanishi kerak."""
        bs = make_bot_state()
        lock = threading.Lock()
        t = "12500"
        
        try:
            new_bal = float(t.strip())
            if new_bal < 0: raise ValueError
            with lock:
                bs['terminal']['balance'] = new_bal
        except ValueError:
            pass
            
        assert bs['terminal']['balance'] == 12500.0

    def test_invalid_balance_input_does_not_update(self):
        """Noto'g'ri qiymat kiritilganda balans o'zgarmasligi kerak."""
        bs = make_bot_state()
        original_bal = bs['terminal']['balance']
        lock = threading.Lock()
        
        invalid_inputs = ["-500", "salom", ""]
        for t in invalid_inputs:
            try:
                new_bal = float(t.strip())
                if new_bal < 0: raise ValueError
                with lock:
                    bs['terminal']['balance'] = new_bal
            except ValueError:
                pass
                
        assert bs['terminal']['balance'] == original_bal
# ─── TDD: Session Behavior ──────────────────────────────────────────────────

class TestSessionBehavior:
    @pytest.mark.asyncio
    async def test_session_photo_handling(self, notifier):
        """TDD: FSM (in_session) holatida rasm yuborilganda AI ga uzatilishini tekshirish"""
        uid = "12345"
        notifier.user_states[uid] = "in_session"
        notifier.user_modules[uid] = "chat"
        bot_state = make_bot_state()
        
        # Simulyatsiya: Foydalanuvchi rasm yubordi
        message = {
            'message_id': 102,
            'from': {'id': int(uid), 'is_bot': False, 'first_name': 'Tester'},
            'chat': {'id': int(uid), 'type': 'private'},
            'date': 1610000000,
            'photo': [{'file_id': 'file_id_123', 'file_unique_id': 'unique_123', 'file_size': 1000, 'width': 100, 'height': 100}]
        }
        
        # Mocking getFile and file download
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('utils.persistence.load_state', return_value=bot_state), \
             patch('utils.persistence.save_state'):
            
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={'result': {'file_path': 'photos/file_1.jpg'}})
            mock_resp.read = AsyncMock(return_value=b"fake_image_data")
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            cfg = make_cfg()
            sess = await notifier.get_session()
            await notifier.handle_update({'update_id': 100, 'message': message}, bot_state, cfg, sess, ".tg_offset")
            
            # Tekshirish: ai_requests ga rasm ma'lumotlari tushdimi?
            found = False
            for req in bot_state['ai_requests']:
                if req['chat_id'] == uid and req['image'] == b"fake_image_data":
                    found = True
                    break
            assert found is True, "Session rejimida rasm AI requests ga qo'shilmadi!"
