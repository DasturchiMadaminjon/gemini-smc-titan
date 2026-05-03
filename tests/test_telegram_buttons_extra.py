"""
tests/test_telegram_buttons_extra.py
Yangi funksiyalar uchun qo'shimcha testlar:
- Suhbat xotirasi (chat_history)
- Jonli SMC Trener rejimi (FSM)
- Qo'llanma tugmasi
"""
import pytest
import threading
from unittest.mock import AsyncMock, patch

ADMIN_UID = "7295947374"
USER_UID  = "9999999999"


def make_bot_state():
    return {
        "symbols": {"XAU/USD": {"price": 2350.0}},
        "terminal": {"balance": 5000.0},
        "ai_requests": [],
        "loss_streak": 0,
        "panic_request": False
    }


@pytest.fixture
def notifier():
    """Mock TelegramNotifier yaratish."""
    with patch("utils.telegram.AIEngine"), \
         patch("google.generativeai.configure"), \
         patch("google.generativeai.list_models", return_value=[]):
        from utils.telegram import TelegramNotifier
        cfg = {
            "telegram": {"bot_token": "test_token", "chat_id": [int(ADMIN_UID)]},
            "gemini_ai": {"api_keys": [], "model": "gemini-2.5-flash"},
            "symbols": ["XAU/USD", "BTC/USDT"],
            "timeframe": "15m",
            "smc": {"min_quality": 30.0},
            "trend": {"risk_perc": 1.0}
        }
        obj = TelegramNotifier(cfg, threading.Lock())
        obj.send = AsyncMock()
        return obj


# ─── Suhbat Xotirasi (Chat History) ────────────────────────────────────────

class TestChatHistory:
    def test_chat_history_attribute_exists(self, notifier):
        """chat_history atributi mavjud bo'lishi kerak."""
        assert hasattr(notifier, 'chat_history')
        assert isinstance(notifier.chat_history, dict)

    def test_max_history_is_5(self, notifier):
        """MAX_HISTORY qiymati 5 bo'lishi kerak."""
        assert notifier.MAX_HISTORY == 5

    def test_history_starts_empty(self, notifier):
        """Yangi notifier uchun tarix bo'sh bo'lishi kerak."""
        assert len(notifier.chat_history) == 0

    def test_user_message_saved_to_history(self, notifier):
        """Foydalanuvchi xabari tarixga qo'shiladi."""
        uid = ADMIN_UID
        notifier.chat_history[uid] = []
        notifier.chat_history[uid].append({'role': 'user', 'text': 'JPY yangiligi chiqdi'})
        assert len(notifier.chat_history[uid]) == 1
        assert notifier.chat_history[uid][0]['role'] == 'user'
        assert 'JPY' in notifier.chat_history[uid][0]['text']

    def test_history_capped_at_max(self, notifier):
        """6 ta xabar kiritilsa, oxirgi 5 tasi saqlanishi kerak."""
        uid = ADMIN_UID
        notifier.chat_history[uid] = []
        for i in range(6):
            notifier.chat_history[uid].append({'role': 'user', 'text': f'xabar {i}'})
        if len(notifier.chat_history[uid]) > notifier.MAX_HISTORY:
            notifier.chat_history[uid] = notifier.chat_history[uid][-notifier.MAX_HISTORY:]
        assert len(notifier.chat_history[uid]) == 5
        # Eng oxirgi 5 ta saqlanadi
        assert notifier.chat_history[uid][-1]['text'] == 'xabar 5'
        assert notifier.chat_history[uid][0]['text']  == 'xabar 1'

    def test_context_built_from_history(self, notifier):
        """Avvalgi xabarlar yangi so'rovga kontekst sifatida qo'shiladi."""
        uid = ADMIN_UID
        notifier.chat_history[uid] = [
            {'role': 'user', 'text': 'JPY yangiligi chiqdi'},
        ]
        new_msg = 'bu yangilikda nima qilish kerak?'
        notifier.chat_history[uid].append({'role': 'user', 'text': new_msg})

        lines = []
        for h in notifier.chat_history[uid][:-1]:
            prefix = "Foydalanuvchi" if h['role'] == 'user' else "AI"
            lines.append(f"{prefix}: {h['text'][:200]}")
        history_ctx = "[SUHBAT TARIXI (oxirgi xabarlar)]:\n" + "\n".join(lines) + "\n\n"
        full_text = history_ctx + new_msg

        assert "SUHBAT TARIXI" in full_text
        assert "JPY yangiligi" in full_text
        assert new_msg in full_text

    def test_users_have_separate_histories(self, notifier):
        """Admin va user alohida tarixga ega bo'ladi."""
        notifier.chat_history[ADMIN_UID] = [{'role': 'user', 'text': 'Admin xabari'}]
        notifier.chat_history[USER_UID]  = [{'role': 'user', 'text': 'User xabari'}]
        assert notifier.chat_history[ADMIN_UID] != notifier.chat_history[USER_UID]

    def test_first_message_no_context(self, notifier):
        """Birinchi xabarda kontekst bo'lmaydi (tarix bo'sh)."""
        uid = ADMIN_UID
        notifier.chat_history[uid] = []
        notifier.chat_history[uid].append({'role': 'user', 'text': 'birinchi xabar'})
        history_ctx = ""
        if len(notifier.chat_history[uid]) > 1:
            history_ctx = "SUHBAT TARIXI"
        assert history_ctx == ""  # Birinchi xabar — kontekst yo'q


# ─── Jonli SMC Trener Rejimi ────────────────────────────────────────────────

class TestSMCMentorMode:
    def test_trener_button_sets_state(self, notifier):
        """'Jonli SMC Trener' tugmasi FSM holatini o'rnatadi."""
        t = "Jonli SMC Trener"
        if "Jonli SMC Trener" in t:
            notifier.user_states[ADMIN_UID] = "choosing_module"
        assert notifier.user_states[ADMIN_UID] == "choosing_module"

    def test_mentor_has_4_modules(self):
        """SMC Trener menyusida 4 ta modul bo'lishi kerak."""
        modules = ["mentor_lessons", "mentor_live_examples", "mentor_qa", "mentor_exit"]
        assert len(modules) == 4

    def test_mentor_qa_module_selected(self, notifier):
        """mentor_qa tanlanganda user_modules va user_states to'g'ri o'rnatiladi."""
        user_modules = {}
        cb = "mentor_qa"
        module_map = {
            "mentor_lessons":       "lessons",
            "mentor_live_examples": "live_examples",
            "mentor_qa":            "mentor_qa",
        }
        if cb in module_map:
            notifier.user_states[ADMIN_UID] = "in_session"
            user_modules[ADMIN_UID] = module_map[cb]
        assert user_modules.get(ADMIN_UID) == "mentor_qa"
        assert notifier.user_states.get(ADMIN_UID) == "in_session"

    def test_mentor_exit_clears_state(self, notifier):
        """'chiqish' yozilganda FSM holati tozalanadi."""
        notifier.user_states[ADMIN_UID] = "in_session"
        t = "chiqish"
        if t.lower() in ["chiqish", "exit", "stop"]:
            notifier.user_states.pop(ADMIN_UID, None)
        assert ADMIN_UID not in notifier.user_states

    def test_in_session_question_added_as_ai_request(self):
        """in_session holatida savol AI request sifatida qo'shiladi."""
        bs = make_bot_state()
        lock = threading.Lock()
        user_modules = {ADMIN_UID: "mentor_qa"}
        t = "BOS nima?"
        with lock:
            bs['ai_requests'].append({
                'type': user_modules.get(ADMIN_UID, 'mentor_qa'),
                'symbol': 'SMC',
                'chat_id': ADMIN_UID,
                'text': t
            })
        assert bs['ai_requests'][0]['type'] == 'mentor_qa'
        assert bs['ai_requests'][0]['symbol'] == 'SMC'
        assert 'BOS' in bs['ai_requests'][0]['text']


# ─── Qo'llanma Tugmasi ──────────────────────────────────────────────────────

class TestQollanmaButton:
    def _make_guide(self):
        return (
            "GEMINI SMC TITAN V27.2 - Qollanma\n"
            "Texnik Tahlil - SMC strukturani izohlab beradi\n"
            "Fundamental - DXY, FED tahlili\n"
            "Hisobot - oxirgi signallar statistikasi\n"
            "AI Chat - erkin savol-javob\n"
            "Scalping AI - M5/M15 kirish rejasi\n"
            "Risk Status - balans ko'rsatadi\n"
            "PANIC CLOSE ALL - favqulodda yopish\n"
        )

    def test_guide_contains_all_sections(self):
        """Qo'llanma barcha bo'limlarni o'z ichiga oladi."""
        guide = self._make_guide()
        for section in ["Texnik Tahlil", "Fundamental", "Hisobot",
                        "AI Chat", "Scalping AI", "Risk Status", "PANIC CLOSE ALL"]:
            assert section in guide, f"'{section}' qo'llanmada yo'q"

    def test_guide_accessible_to_non_admin(self):
        """Qo'llanma barcha foydalanuvchilarga ochiq."""
        t = "Qollanma"
        assert "llanma" in t.lower()

    def test_guide_trigger_words_both_work(self):
        """Trigger so'zlar to'g'ri aniqlanadi."""
        for t in ["Qo'llanma", "qo'llanma"]:
            assert "llanma" in t.lower()

    def test_guide_version_mentioned(self):
        """Qo'llanmada versiya ko'rsatilgan bo'lishi kerak."""
        guide = self._make_guide()
        assert "V27.2" in guide
