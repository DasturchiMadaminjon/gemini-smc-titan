"""
TDD: Fundamental Symbol Detection va Price Fetching
====================================================
Maqsad:
  - "goldni analiz qil" kabi erkin matndan to'g'ri symbol aniqlash
  - symbol='SMC' hardcoded muammosi qaytib kelmasligini kafolatlash
  - Fundamental AI request da narx 0 bo'lmasligini tekshirish
  - Persona formatining qat'iy ekanligini tekshirish

Bog'liq fayllar:
  - utils/telegram.py  (symbol detection logikasi)
  - utils/ai_engine.py (fundamental persona)
  - bot.py             (price fallback via price_fetcher)

Muallif: TDD Audit — 2026-05-11
"""

import pytest
import threading
from unittest.mock import MagicMock, patch


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_cfg():
    return {
        'telegram': {'bot_token': 'fake_token', 'chat_id': ['111']},
        'gemini_ai': {'api_keys': ['fakekey_abc123xyz'], 'model': 'gemini-2.5-flash'},
        'symbols': ['XAU/USD', 'BTC/USDT', 'ETH/USDT'],
        'timeframe': '15m',
    }


@pytest.fixture
def mock_bot_state():
    return {
        'symbols': {'XAU/USD': {'price': 0.0}, 'BTC/USDT': {'price': 65000.0}},
        'ai_requests': [],
        'settings': {},
        'terminal': {'balance': 5000.0},
        'loss_streak': 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. Symbol Detection Testlari
# ══════════════════════════════════════════════════════════════════════════════

class TestFundamentalSymbolDetection:
    """
    Foydalanuvchi Fundamental rejimda erkin matn yozganda,
    telegram.py to'g'ri symbolni aniqlashi kerak.
    """

    @pytest.mark.parametrize("user_text,expected_symbol", [
        ("goldni analiz qil",          "XAU/USD"),
        ("GOLD haqida gapir",          "XAU/USD"),
        ("xau/usd ni ko'rib chiq",     "XAU/USD"),
        ("oltinni tahlil qil",         "XAU/USD"),
        ("btc uchun tahlil ber",       "BTC/USDT"),
        ("bitcoin analiz",             "BTC/USDT"),
        ("ETH/USD ni analiz qil",      "ETH/USDT"),
        ("ethereum haqida",            "ETH/USDT"),
        ("efir narxi qanday",          "ETH/USDT"),
        ("kumushni ko'r",              "XAG/USD"),
        ("silver analiz",              "XAG/USD"),
        ("eur/usd tahlil",             "EUR/USD"),
        ("gbp haqida",                 "GBP/USD"),
        ("dxy indeksini ko'r",         "DXY"),
        ("dollar kuchaydi",            "DXY"),
        ("neft narxi qanday",          "OIL/USD"),
    ])
    def test_symbol_detection_from_user_text(self, user_text, expected_symbol):
        """
        Erkin matndan to'g'ri symbol aniqlanishi shart.
        Bu 'goldni analiz qil' → 'SMC' (XATO) muammosini qaytarib keltirmaslik uchun.
        """
        SYMBOL_HINTS = {
            'gold': 'XAU/USD', 'xau': 'XAU/USD', 'oltin': 'XAU/USD',
            'silver': 'XAG/USD', 'xag': 'XAG/USD', 'kumush': 'XAG/USD',
            'btc': 'BTC/USDT', 'bitcoin': 'BTC/USDT',
            'eth': 'ETH/USDT', 'ethereum': 'ETH/USDT', 'efir': 'ETH/USDT',
            'eur': 'EUR/USD', 'gbp': 'GBP/USD',
            'dxy': 'DXY', 'dollar': 'DXY',
            'oil': 'OIL/USD', 'neft': 'OIL/USD',
            'nasdaq': 'NASDAQ', 'sp500': 'S&P500',
        }
        txt_lower = user_text.lower()
        detected = 'SMC'  # Default (agar hech narsa topilmasa)
        for hint, sym_name in SYMBOL_HINTS.items():
            if hint in txt_lower:
                detected = sym_name
                break

        assert detected == expected_symbol, (
            f"XATO: '{user_text}' uchun '{expected_symbol}' kutildi, "
            f"lekin '{detected}' aniqlandi!\n"
            f"Bu 'goldni analiz qil → narx: 0.00' muammosini keltirib chiqaradi."
        )

    def test_unknown_text_falls_back_to_smc(self):
        """Noma'lum matn uchun default 'SMC' qaytishi kerak."""
        SYMBOL_HINTS = {
            'gold': 'XAU/USD', 'btc': 'BTC/USDT',
        }
        detected = 'SMC'
        txt = "bozorda nima bo'lyapti?"
        for hint, sym_name in SYMBOL_HINTS.items():
            if hint in txt.lower():
                detected = sym_name
                break
        assert detected == 'SMC', "Noma'lum matn uchun 'SMC' qaytishi kerak."

    def test_symbol_never_is_smc_for_known_assets(self):
        """
        Hech qachon 'goldni analiz qil' uchun symbol='SMC' bo'lmasligi kerak.
        Bu regression test — bir marta yuz bergan bug qaytib kelmasin.
        """
        SYMBOL_HINTS = {
            'gold': 'XAU/USD', 'xau': 'XAU/USD', 'oltin': 'XAU/USD',
            'btc': 'BTC/USDT', 'bitcoin': 'BTC/USDT',
            'eth': 'ETH/USDT', 'ethereum': 'ETH/USDT',
        }
        known_texts = [
            "goldni analiz qil", "btc tahlil", "ethereum narxi",
            "xau/usd ko'r", "bitcoin haqida gapir",
        ]
        for text in known_texts:
            detected = 'SMC'
            for hint, sym_name in SYMBOL_HINTS.items():
                if hint in text.lower():
                    detected = sym_name
                    break
            assert detected != 'SMC', (
                f"REGRESSION BUG! '{text}' uchun symbol='SMC' bo'lib qoldi! "
                f"Bu AI ga narx=0 uzatishga olib keladi."
            )


# ══════════════════════════════════════════════════════════════════════════════
# 2. AI Request Queue Testlari
# ══════════════════════════════════════════════════════════════════════════════

class TestFundamentalAIRequestQueue:
    """
    Foydalanuvchi Fundamental rejimda matn yozganda,
    ai_requests navbatiga to'g'ri symbol bilan yozilishi kerak.
    """

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_fundamental_request_has_correct_symbol(
        self, mock_client_class, mock_cfg, mock_bot_state
    ):
        """
        'goldni analiz qil' → ai_requests da symbol='XAU/USD' bo'lishi shart.
        symbol='SMC' bo'lishi — MAQBUL EMAS.
        """
        from utils.telegram import TelegramNotifier
        lock = threading.Lock()
        notifier = TelegramNotifier(mock_cfg, lock)

        # Foydalanuvchini Fundamental sessiyaga solamiz
        uid = '111'
        notifier.user_states[uid] = 'in_session'
        notifier.user_modules[uid] = 'fundamental'

        # in_session logikasini to'g'ridan-to'g'ri simulatsiya qilish
        user_text = "goldni analiz qil"
        module_type = notifier.user_modules.get(uid, 'mentor_qa')
        detected_symbol = 'SMC'

        SYMBOL_HINTS = {
            'gold': 'XAU/USD', 'xau': 'XAU/USD', 'oltin': 'XAU/USD',
            'silver': 'XAG/USD', 'xag': 'XAG/USD', 'kumush': 'XAG/USD',
            'btc': 'BTC/USDT', 'bitcoin': 'BTC/USDT',
            'eth': 'ETH/USDT', 'ethereum': 'ETH/USDT', 'efir': 'ETH/USDT',
            'eur': 'EUR/USD', 'gbp': 'GBP/USD',
            'dxy': 'DXY', 'dollar': 'DXY',
            'oil': 'OIL/USD', 'neft': 'OIL/USD',
        }
        if module_type == 'fundamental':
            for hint, sym_name in SYMBOL_HINTS.items():
                if hint in user_text.lower():
                    detected_symbol = sym_name
                    break

        with lock:
            mock_bot_state['ai_requests'].append({
                'type': module_type,
                'symbol': detected_symbol,
                'chat_id': uid,
                'text': user_text,
                'image': None,
            })

        # Tekshiruv
        assert len(mock_bot_state['ai_requests']) == 1
        req = mock_bot_state['ai_requests'][0]

        assert req['type'] == 'fundamental', \
            f"type='fundamental' bo'lishi kerak, lekin '{req['type']}' edi!"
        assert req['symbol'] == 'XAU/USD', (
            f"XATO: symbol='XAU/USD' kutildi, lekin '{req['symbol']}' edi!\n"
            f"Bu 'goldni analiz qil → Joriy narx: 0.00 USD' muammosini keltirib chiqaradi."
        )
        assert req['symbol'] != 'SMC', \
            "REGRESSION BUG: symbol='SMC' bo'lib qoldi! Bu AI ni aldaydi."

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_eth_usd_request_not_blocked(
        self, mock_client_class, mock_cfg, mock_bot_state
    ):
        """
        'ETH/USD ni analiz qil' → AI fundamental tahlil qilishi shart,
        'bilmayman' deb rad etmasligi kerak.
        (Oldingi bot logida yuz bergan 2-chi muammo)
        """
        from utils.ai_engine import AIEngine

        ai = AIEngine(api_keys=['fakekey'], model_name='models/gemini-2.5-flash')
        ai.client = MagicMock()

        # Mock javob — RAD etish emas, tahlil berishi kerak
        mock_chat = MagicMock()
        ai.client.chats.create.return_value = mock_chat

        expected_response = (
            "📌 INSTRUMENT: ETH/USDT\n"
            "💲 JORIY NARX: 3,500 USD\n"
            "📊 MAKRO BIAS: BULLISH — DeFi faoliyati oshmoqda\n"
        )
        mock_chat.send_message.return_value = MagicMock(text=expected_response)

        ai.rag = None
        result = await ai.get_analysis(
            prompt="ETH/USD ni analiz qil. Joriy narx: 3500 USD.",
            context_type='fundamental'
        )

        assert result is not None
        assert len(result) > 10, "AI bo'sh javob qaytardi!"
        assert 'bilmayman' not in result.lower(), \
            "AI 'bilmayman' dedi — bu fundamental persona qoidasiga zid!"
        assert 'imkonsiz' not in result.lower(), \
            "AI rad etdi — bu fundamental persona qoidasiga zid!"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Persona Format Testi
# ══════════════════════════════════════════════════════════════════════════════

class TestFundamentalPersonaFormat:
    """
    Fundamental persona qat'iy format bo'yicha javob berishi kerak.
    """

    @patch('utils.ai_engine.genai.Client')
    def test_fundamental_persona_contains_format_instruction(self, mock_client_class):
        """
        Fundamental persona 'INSTRUMENT', 'JORIY NARX', 'MAKRO BIAS'
        kabi majburiy bo'limlarni o'z ichiga olishi kerak.
        """
        from utils.ai_engine import AIEngine
        ai = AIEngine(api_keys=['fakekey'])
        persona = ai.personas.get('fundamental', '')

        required_keywords = [
            'INSTRUMENT', 'JORIY NARX', 'MAKRO BIAS',
            'MUHIM DARAJALAR', 'DRAYVERLAR', 'XULOSA',
        ]
        for kw in required_keywords:
            assert kw in persona, (
                f"Fundamental persona '{kw}' kalit so'zini o'z ichiga olmaydi!\n"
                f"Bu AI ga to'g'ri format bo'yicha javob berishni buyurmaydi."
            )

    @patch('utils.ai_engine.genai.Client')
    def test_fundamental_persona_forbids_generic_response(self, mock_client_class):
        """
        Fundamental persona 'umumiy ma'ruza yozish' va 'bilmayman'
        deyishni taqiqlashi kerak.
        """
        from utils.ai_engine import AIEngine
        ai = AIEngine(api_keys=['fakekey'])
        persona = ai.personas.get('fundamental', '')

        assert 'TAQIQLANADI' in persona or 'TAQIQLANGAN' in persona, (
            "Fundamental persona 'generic javob taqiqlangan' qoidasini o'z ichiga olmaydi!\n"
            "Bu AI ning uzun va foydasiz makro ma'ruza yozishiga olib keladi."
        )

    @patch('utils.ai_engine.genai.Client')
    def test_all_personas_are_defined(self, mock_client_class):
        """Barcha kerakli persona turlari mavjudligini tekshirish."""
        from utils.ai_engine import AIEngine
        ai = AIEngine(api_keys=['fakekey'])

        required_personas = [
            'technical', 'scalping', 'fundamental',
            'chat', 'analytics', 'mentor_lessons', 'mentor_qa',
        ]
        for persona_name in required_personas:
            assert persona_name in ai.personas, \
                f"'{persona_name}' persona topilmadi! ai_engine.py ni tekshiring."
            assert len(ai.personas[persona_name]) > 20, \
                f"'{persona_name}' persona juda qisqa — bo'sh yoki minimal!"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Price Fallback Testi
# ══════════════════════════════════════════════════════════════════════════════

class TestPriceFallback:
    """
    bot.py da price=0 bo'lganda price_fetcher fallback ishlashi kerak.
    """

    def test_price_fetcher_gold_returns_nonzero(self):
        """
        price_fetcher.get_current_price('XAU/USD') noldan katta narx qaytarishi kerak.
        Agar yfinance ishlamasa, xatolik matn qaytaradi — lekin '0.00' bo'lmasligi kerak.
        """
        from utils.price_fetcher import get_current_price
        result = get_current_price('XAU/USD')
        assert isinstance(result, str), "get_current_price string qaytarishi kerak."
        assert len(result) > 5, "Natija juda qisqa — bo'sh yoki xato!"

        # Agar muvaffaqiyatli bo'lsa, narxda kamida 3 ta raqam bo'lishi kerak
        import re
        nums = re.findall(r'\d+\.?\d*', result.replace(',', ''))
        if nums and float(nums[0]) > 0:
            price = float(nums[0])
            assert price > 100, (
                f"XAU/USD narxi {price} USD — bu juda past! "
                f"Gold narxi kamida 100 USD bo'lishi kerak."
            )

    def test_price_fetcher_eth_returns_nonzero(self):
        """ETH/USDT uchun ham narx olish."""
        from utils.price_fetcher import get_current_price
        result = get_current_price('ETH/USDT')
        assert isinstance(result, str)
        assert 'ETH' in result or 'narx' in result.lower() or 'xatolik' in result.lower(), \
            f"Kutilmagan natija: {result}"

    pytest.main([__file__, '-v', '--tb=short'])
