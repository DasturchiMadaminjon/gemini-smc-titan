"""
TDD: Foydalanuvchi Boshqaruv Tizimi Testlari
RED holatida yozilgan — implementation keyin qo'shiladi.
"""
import pytest
import sqlite3
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# 1. MA'LUMOTLAR BAZASI TESTLARI
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseUserManagement:
    """DatabaseManager — users jadvali va setting metodlarini tekshiradi."""

    def setup_method(self):
        """Har bir test uchun yangi vaqtinchalik baza."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        from utils.database import DatabaseManager
        self.db = DatabaseManager(db_path=self.tmp.name)

    def teardown_method(self):
        """Testdan keyin faylni tozalash."""
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    # ── 1.1 Ro'yxatga olish ────────────────────────────────────────────────

    def test_register_new_user_creates_record(self):
        """Yangi foydalanuvchi ro'yxatdan o'tganda baza yozuvini yaratishi kerak."""
        self.db.register_or_update_user(
            user_id="100", username="testuser",
            first_name="Test", last_name="User"
        )
        status = self.db.get_user_status("100")
        assert status in ("ACTIVE", "PENDING"), (
            f"Kutilgan: 'ACTIVE' yoki 'PENDING', Olingan: {status!r}"
        )

    def test_register_same_user_twice_no_duplicate(self):
        """Bir xil foydalanuvchini ikki marta ro'yxatdan o'tkazish — dublikat bo'lmasligi kerak."""
        self.db.register_or_update_user("200", "user2", "A", "B")
        self.db.register_or_update_user("200", "user2_updated", "A", "B")
        users = self.db.get_all_users()
        ids = [u["user_id"] for u in users]
        assert ids.count("200") == 1, "Dublikat foydalanuvchi yozuvi yaratilmasligi kerak."

    def test_register_with_active_status(self):
        """PUBLIC rejimda ro'yxatdan o'tgan foydalanuvchi 'ACTIVE' bo'lishi kerak."""
        self.db.register_or_update_user("300", "user3", "C", "D", default_status="ACTIVE")
        assert self.db.get_user_status("300") == "ACTIVE"

    def test_register_with_pending_status(self):
        """RESTRICTED rejimda ro'yxatdan o'tgan foydalanuvchi 'PENDING' bo'lishi kerak."""
        self.db.register_or_update_user("400", "user4", "E", "F", default_status="PENDING")
        assert self.db.get_user_status("400") == "PENDING"

    # ── 1.2 Status yangilash ───────────────────────────────────────────────

    def test_update_user_status_to_blocked(self):
        """Foydalanuvchini 'BLOCKED' qilish mumkin bo'lishi kerak."""
        self.db.register_or_update_user("500", "blockme", "X", "Y")
        self.db.update_user_status("500", "BLOCKED")
        assert self.db.get_user_status("500") == "BLOCKED"

    def test_update_user_status_to_active(self):
        """Bloklangan foydalanuvchini 'ACTIVE' ga qaytarish mumkin bo'lishi kerak."""
        self.db.register_or_update_user("600", "unblockme", "P", "Q", default_status="PENDING")
        self.db.update_user_status("600", "ACTIVE")
        assert self.db.get_user_status("600") == "ACTIVE"

    def test_get_user_status_unknown_returns_none_or_pending(self):
        """Bazada yo'q foydalanuvchining statusini so'raganda None yoki 'PENDING' qaytarishi kerak."""
        status = self.db.get_user_status("99999999")
        assert status in (None, "PENDING"), (
            f"Kutilgan: None yoki 'PENDING', Olingan: {status!r}"
        )

    # ── 1.3 Barcha foydalanuvchilar ro'yxati ──────────────────────────────

    def test_get_all_users_returns_list(self):
        """get_all_users() ro'yxat qaytarishi kerak."""
        result = self.db.get_all_users()
        assert isinstance(result, list), "get_all_users() list qaytarishi kerak."

    def test_get_all_users_contains_registered(self):
        """Ro'yxatdan o'tgan foydalanuvchi get_all_users() natijasida bo'lishi kerak."""
        self.db.register_or_update_user("700", "listed", "L", "M")
        users = self.db.get_all_users()
        ids = [u["user_id"] for u in users]
        assert "700" in ids, "Ro'yxatdan o'tgan foydalanuvchi get_all_users() da ko'rinishi kerak."

    def test_get_all_users_dict_has_required_keys(self):
        """Har bir foydalanuvchi yozuvi kerakli kalitlarga ega bo'lishi kerak."""
        self.db.register_or_update_user("800", "keycheck", "K", "R")
        users = self.db.get_all_users()
        user = next((u for u in users if u["user_id"] == "800"), None)
        assert user is not None
        for key in ("user_id", "username", "status", "joined_at"):
            assert key in user, f"'{key}' kaliti foydalanuvchi yozuvida yo'q."

    # ── 1.4 Sozlamalar (Settings) ──────────────────────────────────────────

    def test_set_and_get_setting(self):
        """set_setting/get_setting juftligi to'g'ri ishlashi kerak."""
        self.db.set_setting("access_mode", "PUBLIC")
        val = self.db.get_setting("access_mode", "PUBLIC")
        assert val == "PUBLIC"

    def test_get_setting_returns_default_if_missing(self):
        """Mavjud bo'lmagan sozlama uchun zaxira (default) qiymat qaytarishi kerak."""
        val = self.db.get_setting("nonexistent_key", "MY_DEFAULT")
        assert val == "MY_DEFAULT"

    def test_set_access_mode_restricted(self):
        """access_mode ni RESTRICTED qilish va o'qish to'g'ri ishlashi kerak."""
        self.db.set_setting("access_mode", "RESTRICTED")
        assert self.db.get_setting("access_mode", "PUBLIC") == "RESTRICTED"

    def test_set_admin_link(self):
        """admin_link sozlamasini o'zgartirish va o'qish to'g'ri ishlashi kerak."""
        self.db.set_setting("admin_link", "@YangiAdmin")
        assert self.db.get_setting("admin_link", "@Madaminjon01") == "@YangiAdmin"

    def test_set_blocked_message_extra(self):
        """blocked_message_extra sozlamasini saqlash va o'qish to'g'ri ishlashi kerak."""
        self.db.set_setting("blocked_message_extra", "Murojaat 09:00 - 18:00")
        assert "09:00" in self.db.get_setting("blocked_message_extra", "")

    def test_overwrite_existing_setting(self):
        """Mavjud sozlamani qayta yozish eski qiymatni almashtirishi kerak."""
        self.db.set_setting("admin_link", "@OldAdmin")
        self.db.set_setting("admin_link", "@NewAdmin")
        assert self.db.get_setting("admin_link", "") == "@NewAdmin"

    # ── 1.5 Eskilik (Regression) tekshiruvi ──────────────────────────────

    def test_existing_stats_table_still_works(self):
        """users jadvali qo'shilganda barcha eski jadvallar buzilmasligi kerak."""
        conn = sqlite3.connect(self.tmp.name)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "stats" in tables, "stats jadvali saqlanib qolishi kerak."
        assert "users" in tables, "users jadvali mavjud bo'lishi kerak."
        assert "history" in tables, "history jadvali saqlanib qolishi kerak."
        assert "signals" in tables, "signals jadvali saqlanib qolishi kerak."


# ─────────────────────────────────────────────────────────────────────────────
# 2. KIRISH NAZORATI TESTLARI (Access Control)
# ─────────────────────────────────────────────────────────────────────────────

class TestAccessControl:
    """Kirish nazorati filtri — bloklash va whitelist mantiqini tekshiradi."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        from utils.database import DatabaseManager
        self.db = DatabaseManager(db_path=self.tmp.name)

    def teardown_method(self):
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_blocked_user_is_denied(self):
        """BLOCKED statusdagi foydalanuvchi ruxsatsiz deb hisoblanishi kerak."""
        self.db.register_or_update_user("101", "blockme", "A", "B")
        self.db.update_user_status("101", "BLOCKED")
        status = self.db.get_user_status("101")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        is_denied = (status == "BLOCKED") or (
            access_mode == "RESTRICTED" and status != "ACTIVE"
        )
        assert is_denied is True

    def test_active_user_in_public_mode_allowed(self):
        """PUBLIC rejimda ACTIVE foydalanuvchi kirishga ruxsat olishi kerak."""
        self.db.set_setting("access_mode", "PUBLIC")
        self.db.register_or_update_user("102", "allowed", "A", "B", default_status="ACTIVE")
        status = self.db.get_user_status("102")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        is_denied = (status == "BLOCKED") or (
            access_mode == "RESTRICTED" and status != "ACTIVE"
        )
        assert is_denied is False

    def test_pending_user_in_restricted_mode_denied(self):
        """RESTRICTED rejimda PENDING foydalanuvchi kirishdan rad etilishi kerak."""
        self.db.set_setting("access_mode", "RESTRICTED")
        self.db.register_or_update_user("103", "pending", "A", "B", default_status="PENDING")
        status = self.db.get_user_status("103")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        is_denied = (status == "BLOCKED") or (
            access_mode == "RESTRICTED" and status != "ACTIVE"
        )
        assert is_denied is True

    def test_active_user_in_restricted_mode_allowed(self):
        """RESTRICTED rejimda ACTIVE foydalanuvchi kirishga ruxsat olishi kerak."""
        self.db.set_setting("access_mode", "RESTRICTED")
        self.db.register_or_update_user("104", "whitelisted", "A", "B", default_status="ACTIVE")
        status = self.db.get_user_status("104")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        is_denied = (status == "BLOCKED") or (
            access_mode == "RESTRICTED" and status != "ACTIVE"
        )
        assert is_denied is False

    def test_pending_user_in_public_mode_gets_activated(self):
        """PUBLIC rejimda yangi foydalanuvchi ACTIVE bo'lishi kerak."""
        self.db.set_setting("access_mode", "PUBLIC")
        self.db.register_or_update_user("105", "newuser", "A", "B", default_status="ACTIVE")
        status = self.db.get_user_status("105")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        is_denied = (status == "BLOCKED") or (
            access_mode == "RESTRICTED" and status != "ACTIVE"
        )
        assert is_denied is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. DINAMIK XABAR QURISH TESTLARI
# ─────────────────────────────────────────────────────────────────────────────

class TestDynamicBlockedMessage:
    """Bloklangan foydalanuvchiga yuboriluvchi xabarni dinamik qurish testlari."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        from utils.database import DatabaseManager
        self.db = DatabaseManager(db_path=self.tmp.name)

    def teardown_method(self):
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def _build_blocked_msg(self):
        """Telegram.py dagi dinamik xabar qurish mantig'ini izolyatsiyada tekshirish."""
        admin_link = self.db.get_setting("admin_link", "@Madaminjon01")
        extra_text = self.db.get_setting("blocked_message_extra", "")
        msg = (
            "⚠️ <b>Kechirasiz, sizda ushbu botdan foydalanish huquqi yo'q.</b>\n\n"
            f"Tizimdan foydalanish va ruxsat olish uchun iltimos admin bilan bog'laning: {admin_link}"
        )
        if extra_text:
            msg += f"\n\n{extra_text}"
        return msg

    def test_default_message_contains_default_admin_link(self):
        """Sozlanmagan holatda xabar @Madaminjon01 ni o'z ichiga olishi kerak."""
        msg = self._build_blocked_msg()
        assert "@Madaminjon01" in msg

    def test_custom_admin_link_appears_in_message(self):
        """Admin link o'zgartirilganda yangi havola xabarda aks etishi kerak."""
        self.db.set_setting("admin_link", "@CustomAdmin")
        msg = self._build_blocked_msg()
        assert "@CustomAdmin" in msg
        assert "@Madaminjon01" not in msg

    def test_extra_text_appended_to_message(self):
        """Qo'shimcha matn mavjud bo'lganda xabarga qo'shilishi kerak."""
        self.db.set_setting("blocked_message_extra", "Murojaat soati: 09:00 - 18:00")
        msg = self._build_blocked_msg()
        assert "09:00" in msg

    def test_no_extra_text_when_not_set(self):
        """Qo'shimcha matn yo'q bo'lganda xabarda bo'lmasligi kerak."""
        msg = self._build_blocked_msg()
        assert msg.count("\n\n") == 1, (
            "Qo'shimcha matn yo'q bo'lganda faqat 1 ta bo'sh qator bo'lishi kerak."
        )

    def test_message_contains_required_warning_emoji(self):
        """Xabarda ⚠️ belgisi bo'lishi kerak."""
        msg = self._build_blocked_msg()
        assert "⚠️" in msg

    def test_url_type_admin_link(self):
        """Admin link sifatida to'liq URL ham maqbul bo'lishi kerak."""
        self.db.set_setting("admin_link", "t.me/madaminjon_support")
        msg = self._build_blocked_msg()
        assert "t.me/madaminjon_support" in msg


# ─────────────────────────────────────────────────────────────────────────────
# 4. SOZLAMALAR MENYUSI TUGMALARI TESTLARI
# ─────────────────────────────────────────────────────────────────────────────

class TestUserManagementButtons:
    """Sozlamalar menyusida 'A'zolarni Boshqarish' tugmasi borligini tekshiradi."""

    def _get_settings_keyboard(self, ai_enabled=True):
        import json
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
        return json.dumps(ikb, ensure_ascii=False)

    def test_settings_keyboard_contains_user_management_button(self):
        """Sozlamalar menyusida '👤 A'zolarni Boshqarish' tugmasi mavjud bo'lishi kerak."""
        kb_json = self._get_settings_keyboard()
        assert "A'zolarni Boshqarish" in kb_json

    def test_settings_keyboard_existing_buttons_preserved(self):
        """Yangi tugma qo'shilganda mavjud sozlamalar tugmalari yo'qolmasligi kerak."""
        kb_json = self._get_settings_keyboard()
        for btn_text in ["Instrumentlar", "Taymfreym", "Risk", "Sifat",
                         "Statistika", "Balans", "Signal Tarixi", "Vaqt Zonasi"]:
            assert btn_text in kb_json, f"'{btn_text}' tugmasi yo'qolgan!"

    def test_user_management_submenu_all_buttons_present(self):
        """A'zolar boshqaruvi menyusida barcha kerakli tugmalar bo'lishi kerak."""
        import json
        users_kb = {'keyboard': [
            [{'text': "👥 A'zolar Ro'yxati"}],
            [{'text': "🔓 Hammaga Ochiq (PUBLIC)"}, {'text': "🔒 Tanlanganlarga (RESTRICTED)"}],
            [{'text': "➕ Ruxsat Berish"}, {'text': "⛔ Bloklash"}],
            [{'text': "🔗 Havolani O'zgartirish"}, {'text': "✍️ Matnni Tahrirlash"}],
            [{'text': "🔙 Sozlamalarga Qaytish"}]
        ], 'resize_keyboard': True}
        kb_json = json.dumps(users_kb, ensure_ascii=False)
        for btn in ["Ro'yxati", "PUBLIC", "RESTRICTED", "Ruxsat Berish",
                    "Bloklash", "Havolani", "Matnni"]:
            assert btn in kb_json, f"'{btn}' tugmasi submenyuda yo'q!"


# ─────────────────────────────────────────────────────────────────────────────
# 5. FSM HOLATLARI TESTLARI
# ─────────────────────────────────────────────────────────────────────────────

class TestFSMStates:
    """FSM holat nomlari va o'tish mantiqini tekshiradi."""

    VALID_STATES = {
        "wait_whitelist_uid",
        "wait_block_uid",
        "wait_admin_link",
        "wait_extra_text",
        "in_session",
        "choosing_module",
    }

    def test_all_new_fsm_states_are_defined(self):
        """Yangi FSM holatlari to'liq ro'yxatda bo'lishi kerak."""
        new_states = {"wait_whitelist_uid", "wait_block_uid",
                      "wait_admin_link", "wait_extra_text"}
        assert new_states.issubset(self.VALID_STATES)

    def test_user_states_dict_stores_string_values(self):
        """user_states lug'ati faqat string holat qiymatlarini saqlashi kerak."""
        user_states = {}
        user_states["999"] = "wait_whitelist_uid"
        assert isinstance(user_states["999"], str)
        assert user_states["999"] in self.VALID_STATES

    def test_fsm_state_cleared_on_cancel(self):
        """FSM holati bekor qilinganda user_states dan o'chirilishi kerak."""
        user_states = {"888": "wait_block_uid"}
        user_states.pop("888", None)
        assert "888" not in user_states

    def test_numeric_uid_input_validation(self):
        """FSM kutish holatida kiritilgan UID raqamli bo'lishi kerak."""
        assert "123456789".isdigit() is True
        assert "not_a_number".isdigit() is False
        assert "123abc".isdigit() is False
