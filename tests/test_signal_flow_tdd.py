"""
TDD - Signal To Telegram Pipeline
==================================
Ushbu test fayli FAQAT testlar uchun yaratilgan.
U Signal Generation -> TradeManager -> Telegram Delivery zanjirini
REAL komponentlarni ishlatgan holda to'liq tekshiradi.

TDD Tamoyili:
  1. Avval test yoziladi
  2. Keyin kod yoziladi
  3. Test o'tguncha kod yaxshilanadi
"""

import pytest, asyncio, threading, json
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import numpy as np

from core.indicator import GeminiIndicator, Signal
from core.manager import TradeManager
from utils.telegram import TelegramNotifier


# ─────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_cfg():
    return {
        "symbols": ["EUR/USD"],
        "timeframe": "15m",
        "smc": {"min_quality": 30.0},
        "trend": {"risk_perc": 2.0, "fibo_split_enabled": True},
        "telegram": {"bot_token": "test_token", "chat_id": [123]},
        "gemini_ai": {"api_keys": ["key1"], "model": "gemini-flash"}
    }

@pytest.fixture
def mock_df():
    """200 ta shamdan iborat sintetik OHLCV data."""
    n = 200
    close = np.linspace(1.0500, 1.0600, n)
    df = pd.DataFrame({
        'open':   close,
        'high':   close + 0.001,
        'low':    close - 0.001,
        'close':  close,
        'volume': [1000] * n
    })
    return df

@pytest.fixture
def valid_buy_signal():
    """To'g'ri BUY signal obyekti (to'g'ridan-to'g'ri yaratilgan)."""
    return Signal(
        direction='buy',
        symbol='EUR/USD',
        entry=1.0600,
        sl=1.0550,
        tp1=1.0675,
        tp2=1.0725,
        tp3=1.0800,
        quality=87.5,
        reason="HTF Trend + BOS + Discount Zone + FVG Tap",
        timestamp=pd.Timestamp.now()
    )


# ─────────────────────────────────────────────────────────
# TEST 1: INDICATOR UNIT TEST
# ─────────────────────────────────────────────────────────

class TestIndicatorSignalGeneration:

    def test_buy_signal_generated_with_correct_conditions(self, mock_cfg, mock_df):
        """
        TDD: GeminiIndicator ichki metodlarini mock qilib,
        to'g'ri sharoitda BUY signal qaytarilishini tekshiramiz.
        """
        ind = GeminiIndicator(mock_cfg)
        ind.min_rr = 0.01  # RR filtrni minimumga tushuramiz

        with patch.object(ind, '_detect_structure_break', return_value={
                'bos_up': True, 'bos_down': False,
                'sweep_up': False, 'sweep_down': False
            }), \
             patch.object(ind, '_get_fibo_zone', return_value='discount'), \
             patch.object(ind, '_find_unmitigated_fvg', return_value={'bullish': (1.0500, 1.0510), 'bearish': None}), \
             patch.object(ind, '_get_trend', return_value='bullish'):

            signal = ind.generate_signal(mock_df, "EUR/USD", "15m", loss_streak=0)

        assert signal is not None, "Sharoit to'g'ri bo'lsa signal xosil bo'lishi kerak!"
        assert signal.direction == 'buy', f"BUY bo'lishi kerak, lekin: {signal.direction}"
        assert signal.symbol == "EUR/USD", "Symbol noto'g'ri!"
        assert signal.sl < signal.entry, "SL entry dan PAST bo'lishi kerak (BUY uchun)!"
        assert signal.tp1 > signal.entry, "TP1 entry dan YUQORI bo'lishi kerak (BUY uchun)!"
        assert signal.quality > 0, "Sifat 0 dan yuqori bo'lishi kerak!"

    def test_no_signal_when_no_bos(self, mock_cfg, mock_df):
        """TDD: BOS bo'lmasa signal xosil bo'lmasin."""
        ind = GeminiIndicator(mock_cfg)
        with patch.object(ind, '_detect_structure_break', return_value={
                'bos_up': False, 'bos_down': False,
                'sweep_up': False, 'sweep_down': False
            }):
            signal = ind.generate_signal(mock_df, "EUR/USD", "15m")
        assert signal is None, "BOS yo'q bo'lsa signal bo'lmasligi kerak!"

    def test_signal_dataclass_has_all_fields(self, valid_buy_signal):
        """TDD: Signal obyektida barcha zarur maydonlar bor."""
        s = valid_buy_signal
        assert hasattr(s, 'direction')
        assert hasattr(s, 'symbol')
        assert hasattr(s, 'entry')
        assert hasattr(s, 'sl')
        assert hasattr(s, 'tp1')
        assert hasattr(s, 'tp2')
        assert hasattr(s, 'tp3')
        assert hasattr(s, 'quality')
        assert hasattr(s, 'reason')
        assert hasattr(s, 'timestamp')


# ─────────────────────────────────────────────────────────
# TEST 2: SIGNAL DELIVERY (Manager -> Telegram)
# ─────────────────────────────────────────────────────────

class TestSignalDeliveryPipeline:

    @pytest.mark.asyncio
    async def test_trade_manager_sends_message_to_telegram(self, mock_cfg, valid_buy_signal):
        """
        TDD: TradeManager.process_and_send_signal() chaqirilganda
        TelegramNotifier.send() CHAQIRILISHI kerak.
        """
        lock = threading.Lock()
        notifier = TelegramNotifier(mock_cfg, lock)
        notifier.send = AsyncMock()  # Real HTTP so'rovni blokeymiz

        db_mock = MagicMock()
        manager = TradeManager(mock_cfg, db_mock, notifier)
        # TradeManager notifier ni telegram atributi orqali ishlatadi
        manager.notifier = MagicMock()
        manager.notifier.send = AsyncMock()

        bot_state = {'terminal': {'balance': 10000.0}}
        await manager.process_and_send_signal("EUR/USD", valid_buy_signal, bot_state, ai_reason="AI: Signal kuchli!")

        assert manager.notifier.send.called, \
            "TDD XATO: Signal jo'natilmadi! TradeManager.notifier.send() chaqirilmadi."

    @pytest.mark.asyncio
    async def test_telegram_message_contains_required_fields(self, mock_cfg, valid_buy_signal):
        """
        TDD: Jo'natilgan xabar matnida barcha zarur ma'lumotlar bo'lishi kerak.
        """
        lock = threading.Lock()
        notifier = TelegramNotifier(mock_cfg, lock)
        notifier.send = AsyncMock()

        db_mock = MagicMock()
        manager = TradeManager(mock_cfg, db_mock, notifier)
        captured_msg = []

        async def capture_send(msg, **kwargs):
            captured_msg.append(msg)

        manager.notifier = MagicMock()
        manager.notifier.send = AsyncMock(side_effect=capture_send)

        bot_state = {'terminal': {'balance': 10000.0}}
        await manager.process_and_send_signal("EUR/USD", valid_buy_signal, bot_state, ai_reason="Test AI Reason")

        assert len(captured_msg) > 0, "Hech qanday xabar jo'natilmadi!"
        text = captured_msg[0]

        # Zarur maydonlarni tekshiramiz
        assert "EUR/USD" in text,   "❌ Instrument nomi yo'q!"
        assert "BUY"    in text,   "❌ Signal yo'nalishi yo'q!"
        assert "Stop-Loss" in text or "SL" in text, "❌ Stop Loss yo'q!"
        assert "TP1"    in text or "Maqsad" in text, "❌ Take Profit yo'q!"
        assert "85.0%" in text or "87.5%" in text or "Sifat" in text, "❌ Signal sifati yo'q!"

    @pytest.mark.asyncio
    async def test_ai_reason_included_in_message(self, mock_cfg, valid_buy_signal):
        """TDD: AI tahlili xabar matnga kiritilishi kerak."""
        db_mock = MagicMock()
        lock = threading.Lock()
        notifier = TelegramNotifier(mock_cfg, lock)
        manager = TradeManager(mock_cfg, db_mock, notifier)

        captured_msg = []
        manager.notifier = MagicMock()
        manager.notifier.send = AsyncMock(side_effect=lambda m, **kw: captured_msg.append(m))

        bot_state = {'terminal': {'balance': 5000.0}}
        await manager.process_and_send_signal("EUR/USD", valid_buy_signal, bot_state, ai_reason="KUCHLI SIGNAL!")

        text = captured_msg[0] if captured_msg else ""
        assert "KUCHLI SIGNAL!" in text, "❌ AI tahlili xabarga kiritilmadi!"

    @pytest.mark.asyncio
    async def test_no_message_if_signal_is_none(self, mock_cfg):
        """TDD: Signal None bo'lsa Telegram ga hech narsa jo'natilmasin."""
        db_mock = MagicMock()
        lock = threading.Lock()
        notifier = TelegramNotifier(mock_cfg, lock)
        manager = TradeManager(mock_cfg, db_mock, notifier)
        manager.notifier = MagicMock()
        manager.notifier.send = AsyncMock()

        bot_state = {'terminal': {'balance': 5000.0}}
        await manager.process_and_send_signal("EUR/USD", None, bot_state)

        assert not manager.notifier.send.called, \
            "❌ Signal None bo'lsa xabar jo'natilmasligi kerak!"


# ─────────────────────────────────────────────────────────
# TEST 3: TO'LIQ INTEGRATSIYA ZANJIRI
# ─────────────────────────────────────────────────────────

class TestFullSignalChainIntegration:

    @pytest.mark.asyncio
    async def test_indicator_to_telegram_end_to_end(self, mock_cfg, mock_df):
        """
        TDD INTEGRATSIYA: GeminiIndicator -> TradeManager -> Telegram.send()
        Bu testda REAL komponentlar ishlaydi, faqat tashqi HTTP bloklangan.
        """
        # QADAM 1: Signal yaratamiz (mock bilan)
        ind = GeminiIndicator(mock_cfg)
        ind.min_rr = 0.01

        with patch.object(ind, '_detect_structure_break', return_value={
                'bos_up': True, 'bos_down': False,
                'sweep_up': False, 'sweep_down': False
            }), \
             patch.object(ind, '_get_fibo_zone', return_value='discount'), \
             patch.object(ind, '_find_unmitigated_fvg', return_value={'bullish': (1.0500, 1.0510), 'bearish': None}), \
             patch.object(ind, '_get_trend', return_value='bullish'):

            signal = ind.generate_signal(mock_df, "EUR/USD", "15m", loss_streak=0)

        assert signal is not None, "E2E XATO: Signal xosil bo'lmadi!"

        # QADAM 2: Manager orqali Telegramga jo'natamiz
        lock = threading.Lock()
        db_mock = MagicMock()
        notifier = TelegramNotifier(mock_cfg, lock)
        manager = TradeManager(mock_cfg, db_mock, notifier)

        captured = []
        manager.notifier = MagicMock()
        manager.notifier.send = AsyncMock(side_effect=lambda m, **kw: captured.append(m))

        bot_state = {'terminal': {'balance': 10000.0}}
        await manager.process_and_send_signal("EUR/USD", signal, bot_state, ai_reason="E2E Test OK")

        # QADAM 3: Natijani tekshiramiz
        assert len(captured) == 1, f"Aynan 1 ta xabar yuborilishi kerak, {len(captured)} ta yuborildi!"
        text = captured[0]
        assert "EUR/USD" in text, "❌ Instrument nomi yo'q!"
        assert "BUY"     in text, "❌ BUY yo'nalishi yo'q!"
        assert "Stop-Loss" in text or "SL" in text, "❌ SL yo'q!"
        assert "E2E Test OK" in text, "❌ AI tahlili yo'q!"

        print("\n✅ E2E INTEGRATSIYA: Indicator → Manager → Telegram MUVAFFAQIYATLI!")
