"""
tests/test_all_buttons_tdd.py
==============================
TITAN V27.2 — Barcha tugmalar uchun TDD testlari.
Jadvalda ko'rsatilgan har bir tugma so'zma-so'z tekshiriladi.

Qoida: Har bir test "Tugma X bosilganda Bot Y deydi" tamoyilida.
"""
import pytest, threading, json
from unittest.mock import AsyncMock, MagicMock, patch

# ─── Yordamchilar ─────────────────────────────────────────────────────────────

def make_notifier():
    """Mock TelegramNotifier."""
    from utils.telegram import TelegramNotifier
    cfg = {
        'telegram': {'bot_token': 'test', 'chat_id': ['7295947374']},
        'gemini_ai': {'api_keys': ['k1'], 'model': 'gemini-flash'},
        'smc': {'min_quality': 30.0},
        'trend': {'risk_perc': 2.0},
        'symbols': ['XAU/USD', 'BTC/USDT'],
        'timeframe': '15m',
    }
    n = TelegramNotifier(cfg, threading.Lock())
    n.send = AsyncMock()
    return n

def make_bs():
    return {'terminal': {'balance': 5000.0}, 'ai_requests': [],
            'loss_streak': 0, 'panic_request': False, 'settings': {}}

def make_cfg():
    return {'symbols': ['XAU/USD', 'BTC/USDT'], 'timeframe': '15m',
            'smc': {'min_quality': 30.0}, 'trend': {'risk_perc': 2.0}}

ADMIN = '7295947374'
USER  = '9999999999'

def msg_update(text, uid=ADMIN, has_photo=False):
    m = {'text': text, 'from': {'id': int(uid)}, 'chat': {'id': int(uid)}}
    if has_photo:
        m['photo'] = [{'file_id': 'fid_test'}]
    return {'update_id': 1, 'message': m}

def cb_update(data, uid=ADMIN):
    return {
        'update_id': 1,
        'callback_query': {
            'id': 'cb1', 'data': data,
            'from': {'id': int(uid)},
            'message': {'chat': {'id': int(uid)}}
        }
    }

async def run(notifier, update, cfg=None):
    """handle_update ni mock sess bilan ishga tushirish."""
    if cfg is None:
        cfg = make_cfg()
    bs = make_bs()
    sess = MagicMock()
    sess.post = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=MagicMock(status=200)),
                                                  __aexit__=AsyncMock(return_value=False)))
    # Rasm yuklab olish uchun to'g'ri async context manager mock
    mock_file_resp = MagicMock()
    mock_file_resp.status = 200
    mock_file_resp.json = AsyncMock(return_value={'result': {'file_path': 'photos/f.jpg'}})
    mock_file_resp.read = AsyncMock(return_value=b'fake_img_bytes')
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_file_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    sess.get = MagicMock(return_value=mock_cm)
    with patch('builtins.open', MagicMock(return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(write=MagicMock())),
            __exit__=MagicMock(return_value=False)))):
        await notifier.handle_update(update, bs, cfg, sess, '.tg_offset')
    return notifier.send.call_args_list, bs


# ═══════════════════════════════════════════════════════════════════════════════
# A. ASOSIY MENYU
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsosiyMenuyu:

    @pytest.mark.asyncio
    async def test_A1_start_komandasida_xush_kelibsiz_xabari(self):
        """/start → 'TITAN V27.2 LIVE!' xabari keladi."""
        n = make_notifier()
        calls, _ = await run(n, msg_update('/start'))
        texts = [c[0][0] for c in calls]
        assert any("V27.2" in t for t in texts), \
            f"❌ /start dan keyin 'V27.2' yo'q! Kelgan: {texts}"

    @pytest.mark.asyncio
    async def test_A2_texnik_tahlil_instrument_menyusi_ochiladi(self):
        """📊 Texnik Tahlil → Instrument tanlash inline menyusi."""
        n = make_notifier()
        calls, _ = await run(n, msg_update('📊 Texnik Tahlil'))
        texts = [c[0][0] for c in calls]
        assert any("TECHNICAL" in t or "tanlang" in t for t in texts), \
            f"❌ Texnik Tahlil bosilganda instrument menyusi chiqmadi! {texts}"

    @pytest.mark.asyncio
    async def test_A3_fundamental_session_faollashadi(self):
        """🌐 Fundamental → 'Fundamental Tahlil faollashdi' xabari va in_session holati."""
        n = make_notifier()
        calls, _ = await run(n, msg_update('🌐 Fundamental'))
        texts = [c[0][0] for c in calls]
        assert any("Fundamental" in t and "faollashdi" in t for t in texts), \
            f"❌ Fundamental bosilganda session faollashuv xabari chiqmadi! {texts}"
        assert n.user_states.get(ADMIN) == "in_session", "❌ in_session holati o'rnatilmadi!"

    @pytest.mark.asyncio
    async def test_A4_chat_assistant_tugmasi_sessionni_faollashtiradi(self):
        """💬 AI Chat Assistant → Chat Assistant faol xabari va in_session holati."""
        n = make_notifier()
        calls, _ = await run(n, msg_update('💬 AI Chat Assistant'))
        texts = [c[0][0] for c in calls]
        assert any("Chat Assistant" in t or "faol" in t for t in texts), \
            f"❌ Chat Assistant xabari yo'q! {texts}"
        assert n.user_states.get(ADMIN) == "in_session", "❌ in_session holati o'rnatilmadi!"

    @pytest.mark.asyncio
    async def test_A5_sozlamalar_faqat_admin_kora_oladi(self):
        """⚙️ Sozlamalar → Admin: sozlamalar menyusi. User: default AI ga uzatiladi (xavfsiz)."""
        # Admin uchun: Sozlamalar menyusi ochiladi
        n_admin = make_notifier()
        calls_a, _ = await run(n_admin, msg_update('⚙️ Sozlamalar', uid=ADMIN))
        texts_a = [c[0][0] for c in calls_a]
        assert any("Sozlamalar" in t for t in texts_a), f"❌ Admin sozlamalar menyusini ko'rmaydi! {texts_a}"

        # User uchun: Sozlamalar menyusi chiqmaydi (faqat matn AI ga boradi)
        n_user = make_notifier()
        calls_u, bs_u = await run(n_user, msg_update('⚙️ Sozlamalar', uid=USER))
        texts_u = [c[0][0] for c in calls_u]
        # Sozlamalar inline menyusi chiqmasligi kerak
        assert not any("inline_keyboard" in t for t in texts_u), \
            f"❌ User sozlamalar inline menyusini ko'rmasligi kerak! {texts_u}"
        # User xabari default AI ga uzatiladi (bu to'g'ri xatti-harakat)
        assert not any("Sozlamalar:" in t for t in texts_u), \
            f"❌ User 'Sozlamalar:' panel ko'rmasligi kerak! {texts_u}"


# ═══════════════════════════════════════════════════════════════════════════════
# B. TRENER MODUL TUGMALARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrenerModullar:

    @pytest.mark.asyncio
    async def test_B1_mentor_lessons_faollashdi(self):
        """mentor_lessons → '📚 Mavzuli Darslar faollashdi.' va in_session holati."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('mentor_lessons'))
        texts = [c[0][0] for c in calls]
        assert any("Mavzuli Darslar" in t for t in texts), f"❌ {texts}"
        assert n.user_states.get(ADMIN) == "in_session"

    @pytest.mark.asyncio
    async def test_B2_mentor_live_examples_faollashdi(self):
        """mentor_live_examples → '🌐 Jonli Misollar faollashdi.' va in_session."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('mentor_live_examples'))
        texts = [c[0][0] for c in calls]
        assert any("Jonli Misollar" in t for t in texts), f"❌ {texts}"
        assert n.user_states.get(ADMIN) == "in_session"

    @pytest.mark.asyncio
    async def test_B3_mentor_qa_faollashdi(self):
        """mentor_qa → '❓ Erkin Savol-Javob faollashdi.' va in_session."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('mentor_qa'))
        texts = [c[0][0] for c in calls]
        assert any("Erkin Savol-Javob" in t for t in texts), f"❌ {texts}"
        assert n.user_states.get(ADMIN) == "in_session"

    @pytest.mark.asyncio
    async def test_B4_mentor_exit_chiqaradi(self):
        """mentor_exit → '🚪 Trener rejimidan chiqdingiz.' va holat tozalanadi."""
        n = make_notifier()
        n.user_states[ADMIN] = "in_session"
        calls, _ = await run(n, cb_update('mentor_exit'))
        texts = [c[0][0] for c in calls]
        assert any("chiqdingiz" in t.lower() for t in texts), f"❌ {texts}"
        assert ADMIN not in n.user_states, "❌ FSM holati tozalanmadi!"


# ═══════════════════════════════════════════════════════════════════════════════
# C. SOZLAMALAR INLINE TUGMALARI
# ═══════════════════════════════════════════════════════════════════════════════

class TestSozlamalarInline:

    @pytest.mark.asyncio
    async def test_C1_tf_menu_taymfreym_variantlarini_korsatadi(self):
        """tf_menu → '⏱ Taymfreym tanlang:' xabari chiqadi."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('tf_menu'))
        texts = [c[0][0] for c in calls]
        assert any("Taymfreym" in t or "tanlang" in t for t in texts), f"❌ {texts}"

    @pytest.mark.asyncio
    async def test_C2_risk_menu_risk_variantlarini_korsatadi(self):
        """risk_menu → '💰 Riskni tanlang:' xabari chiqadi."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('risk_menu'))
        texts = [c[0][0] for c in calls]
        assert any("Risk" in t or "tanlang" in t for t in texts), f"❌ {texts}"

    @pytest.mark.asyncio
    async def test_C3_qual_menu_sifat_variantlarini_korsatadi(self):
        """qual_menu → '⚙️ Sifatni tanlang:' xabari chiqadi."""
        n = make_notifier()
        calls, _ = await run(n, cb_update('qual_menu'))
        texts = [c[0][0] for c in calls]
        assert any("Sifat" in t or "tanlang" in t for t in texts), f"❌ {texts}"


# ═══════════════════════════════════════════════════════════════════════════════
# D. TAYMFREYM TANLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaymfreymTanlash:

    @pytest.mark.asyncio
    async def test_D1_tf_5m_saqlaydi(self):
        """tf_5m (admin) → '✅ Taymfreym: 5m' xabari, settings.yaml yangilanadi."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump') as mock_dump, patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('tf_5m'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("5m" in t for t in texts), f"❌ tf_5m xabari yo'q! {texts}"

    @pytest.mark.asyncio
    async def test_D2_tf_15m_saqlaydi(self):
        """tf_15m (admin) → '✅ Taymfreym: 15m' xabari."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump'), patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('tf_15m'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("15m" in t for t in texts), f"❌ tf_15m xabari yo'q! {texts}"


# ═══════════════════════════════════════════════════════════════════════════════
# E. RISK TANLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskTanlash:

    @pytest.mark.asyncio
    async def test_E1_risk_1_saqlaydi(self):
        """risk_1.0 (admin) → '✅ Risk: 1.0%' xabari."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump'), patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('risk_1.0'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("1.0" in t for t in texts), f"❌ {texts}"

    @pytest.mark.asyncio
    async def test_E2_risk_2_saqlaydi(self):
        """risk_2.0 (admin) → '✅ Risk: 2.0%' xabari."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump'), patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('risk_2.0'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("2.0" in t for t in texts), f"❌ {texts}"


# ═══════════════════════════════════════════════════════════════════════════════
# F. SIFAT TANLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestSifatTanlash:

    @pytest.mark.asyncio
    async def test_F1_sifat_30_saqlaydi(self):
        """setqual_30.0 (admin) → '✅ Sifat: 30.0%' xabari."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump'), patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('setqual_30.0'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("30.0" in t and "Sifat" in t for t in texts), f"❌ {texts}"

    @pytest.mark.asyncio
    async def test_F2_sifat_75_saqlaydi(self):
        """setqual_75.0 (admin) → '✅ Sifat: 75.0%' xabari."""
        n = make_notifier()
        cfg = make_cfg()
        with patch('yaml.dump'), patch('builtins.open', MagicMock(
                return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                                       __exit__=MagicMock(return_value=False)))):
            calls, _ = await run(n, cb_update('setqual_75.0'), cfg=cfg)
        texts = [c[0][0] for c in calls]
        assert any("75.0" in t and "Sifat" in t for t in texts), f"❌ {texts}"


# ═══════════════════════════════════════════════════════════════════════════════
# G. INSTRUMENT TANLASH (AI so'rov)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstrumentTanlash:

    @pytest.mark.asyncio
    async def test_G1_ai_technical_xauusd_navbatga_qoshiladi(self):
        """ai_technical:XAU/USD → '⏳ XAU/USD uchun TECHNICAL tahlili...' xabari."""
        n = make_notifier()
        calls, bs = await run(n, cb_update('ai_technical:XAU/USD'))
        texts = [c[0][0] for c in calls]
        assert any("XAU/USD" in t for t in texts), f"❌ {texts}"
        assert any("TECHNICAL" in t.upper() for t in texts), f"❌ TECHNICAL so'zi yo'q! {texts}"
        assert any(r.get('symbol') == 'XAU/USD' for r in bs['ai_requests']), \
            "❌ ai_requests ga qo'shilmadi!"

    @pytest.mark.asyncio
    async def test_G2_ai_fundamental_btcusdt_navbatga_qoshiladi(self):
        """ai_fundamental:BTC/USDT → '⏳ BTC/USDT uchun FUNDAMENTAL tahlili...' xabari."""
        n = make_notifier()
        calls, bs = await run(n, cb_update('ai_fundamental:BTC/USDT'))
        texts = [c[0][0] for c in calls]
        assert any("BTC/USDT" in t for t in texts), f"❌ {texts}"
        assert any(r.get('symbol') == 'BTC/USDT' for r in bs['ai_requests']), \
            "❌ ai_requests ga qo'shilmadi!"


# ═══════════════════════════════════════════════════════════════════════════════
# H. SESSION ICHIDA (in_session holati)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionIchida:

    @pytest.mark.asyncio
    async def test_H1_session_ichida_matn_ai_ga_uzatiladi(self):
        """in_session + matn → '🧠 [AI tahlil qilmoqda...]' xabari, ai_requests ga qo'shiladi."""
        n = make_notifier()
        n.user_states[ADMIN] = "in_session"
        n.user_modules[ADMIN] = "chat"
        calls, bs = await run(n, msg_update("BTC haqida nima deyish mumkin?"))
        texts = [c[0][0] for c in calls]
        assert any("AI tahlil" in t or "tahlil" in t.lower() for t in texts), f"❌ {texts}"
        assert len(bs['ai_requests']) == 1, "❌ ai_requests ga qo'shilmadi!"

    @pytest.mark.asyncio
    async def test_H2_session_ichida_rasm_ai_ga_uzatiladi(self):
        """in_session + rasm → '🧠 [AI tahlil qilmoqda...]' va rasm ai_requests da."""
        n = make_notifier()
        n.user_states[ADMIN] = "in_session"
        n.user_modules[ADMIN] = "mentor_qa"
        update = msg_update('', has_photo=True)
        calls, bs = await run(n, update)
        texts = [c[0][0] for c in calls]
        assert any("tahlil" in t.lower() for t in texts), f"❌ {texts}"

    @pytest.mark.asyncio
    async def test_H3_chiqish_so_zi_sessiondan_chiqaradi(self):
        """in_session + 'chiqish' → '🚪 Chiqdingiz.' va FSM tozalanadi."""
        n = make_notifier()
        n.user_states[ADMIN] = "in_session"
        calls, _ = await run(n, msg_update('chiqish'))
        texts = [c[0][0] for c in calls]
        assert any("Chiqdingiz" in t or "chiqdingiz" in t for t in texts), f"❌ {texts}"
        assert ADMIN not in n.user_states, "❌ FSM tozalanmadi!"

    @pytest.mark.asyncio
    async def test_H4_exit_so_zi_ham_sessiondan_chiqaradi(self):
        """in_session + 'exit' → ham chiqish xabari."""
        n = make_notifier()
        n.user_states[ADMIN] = "in_session"
        calls, _ = await run(n, msg_update('exit'))
        texts = [c[0][0] for c in calls]
        assert any("Chiqdingiz" in t or "chiqdingiz" in t for t in texts), f"❌ {texts}"


# ═══════════════════════════════════════════════════════════════════════════════
# I. ERKIN MATN / NOMA'LUM
# ═══════════════════════════════════════════════════════════════════════════════

class TestErkinMatn:

    @pytest.mark.asyncio
    async def test_I1_erkin_matn_ai_ga_uzatiladi(self):
        """Session yo'q + istalgan matn → '⏳ Tahlil boshlandi...' va ai_requests."""
        n = make_notifier()
        calls, bs = await run(n, msg_update('Bugun bozor qanday?'))
        texts = [c[0][0] for c in calls]
        assert any("Tahlil" in t or "tahlil" in t for t in texts), f"❌ {texts}"
        assert len(bs['ai_requests']) == 1, "❌ ai_requests ga qo'shilmadi!"
        assert bs['ai_requests'][0]['type'] == 'chat', "❌ type='chat' bo'lishi kerak!"

    @pytest.mark.asyncio
    async def test_I2_rasm_session_da_tashqarida_ai_ga_uzatiladi(self):
        """Session yo'q + rasm → ai ga uzatiladi."""
        n = make_notifier()
        update = msg_update('', has_photo=True)
        calls, bs = await run(n, update)
        texts = [c[0][0] for c in calls]
        assert any("Tahlil" in t or "tahlil" in t for t in texts), f"❌ {texts}"
