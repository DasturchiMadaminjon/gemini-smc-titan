import pytest
import os
from unittest.mock import AsyncMock, patch


class TestDatabaseAIProvider:
    def setup_method(self):
        import tempfile
        self.db_path = tempfile.mktemp(suffix=".db")
        from utils.database import DatabaseManager
        self.db = DatabaseManager(db_path=self.db_path)

    def teardown_method(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_default_ai_provider_is_gemini(self):
        val = self.db.get_setting("ai_provider", "GEMINI")
        assert val == "GEMINI"

    def test_set_ai_provider_to_claude(self):
        self.db.set_setting("ai_provider", "CLAUDE")
        val = self.db.get_setting("ai_provider", "GEMINI")
        assert val == "CLAUDE"

    def test_set_ai_provider_back_to_gemini(self):
        self.db.set_setting("ai_provider", "CLAUDE")
        self.db.set_setting("ai_provider", "GEMINI")
        val = self.db.get_setting("ai_provider", "GEMINI")
        assert val == "GEMINI"

    def test_ai_provider_does_not_affect_other_settings(self):
        self.db.set_setting("access_mode", "RESTRICTED")
        self.db.set_setting("ai_provider", "CLAUDE")
        access_mode = self.db.get_setting("access_mode", "PUBLIC")
        assert access_mode == "RESTRICTED"

    def test_ai_provider_overwrite(self):
        self.db.set_setting("ai_provider", "CLAUDE")
        self.db.set_setting("ai_provider", "GEMINI")
        val = self.db.get_setting("ai_provider", "GEMINI")
        assert val == "GEMINI"


class TestAIEngineClaudeSetup:
    def test_ai_engine_reads_claude_key_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "sk-ant-test-key-123"}):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-gemini-key"])
            assert engine.claude_api_key == "sk-ant-test-key-123"

    def test_ai_engine_claude_key_none_if_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-gemini-key"])
            assert not engine.claude_api_key

    def test_gemini_client_works_without_claude_key(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-gemini-key"])
            assert engine.api_keys == ["fake-gemini-key"]


class TestAIEngineProviderSwitching:
    @pytest.mark.asyncio
    async def test_gemini_provider_calls_gemini_analysis(self):
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "sk-ant-test"}):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-key"])
            engine._get_gemini_analysis = AsyncMock(return_value="Gemini javobi")
            engine._get_claude_analysis = AsyncMock(return_value="Claude javobi")
            result = await engine.get_analysis("test prompt", provider="GEMINI")
            engine._get_gemini_analysis.assert_called_once()
            engine._get_claude_analysis.assert_not_called()
            assert result == "Gemini javobi"

    @pytest.mark.asyncio
    async def test_claude_provider_calls_claude_analysis(self):
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "sk-ant-test"}):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-key"])
            engine.claude_api_key = "sk-ant-real-key"
            engine.claude_client = object()
            engine._get_gemini_analysis = AsyncMock(return_value="Gemini javobi")
            engine._get_claude_analysis = AsyncMock(return_value="Claude javobi")
            result = await engine.get_analysis("test prompt", provider="CLAUDE")
            engine._get_claude_analysis.assert_called_once()
            engine._get_gemini_analysis.assert_not_called()
            assert result == "Claude javobi"

    @pytest.mark.asyncio
    async def test_claude_failure_falls_back_to_gemini(self):
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "sk-ant-test"}):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-key"])
            engine.claude_api_key = "sk-ant-test"
            engine.claude_client = object()
            engine._get_gemini_analysis = AsyncMock(return_value="Gemini fallback")
            engine._get_claude_analysis = AsyncMock(side_effect=Exception("API Error"))
            result = await engine.get_analysis("test prompt", provider="CLAUDE")
            engine._get_gemini_analysis.assert_called_once()
            assert result == "Gemini fallback"

    @pytest.mark.asyncio
    async def test_claude_without_key_falls_back_to_gemini(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            from utils.ai_engine import AIEngine
            engine = AIEngine(api_keys=["fake-key"])
            engine._get_gemini_analysis = AsyncMock(return_value="Gemini javobi")
            engine._get_claude_analysis = AsyncMock(return_value="Claude javobi")
            result = await engine.get_analysis("test prompt", provider="CLAUDE")
            engine._get_gemini_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_provider_defaults_to_gemini(self):
        from utils.ai_engine import AIEngine
        engine = AIEngine(api_keys=["fake-key"])
        engine._get_gemini_analysis = AsyncMock(return_value="Gemini default")
        engine._get_claude_analysis = AsyncMock(return_value="Claude javobi")
        result = await engine.get_analysis("test", provider="NOMA_LUM")
        engine._get_gemini_analysis.assert_called_once()


class TestAIProviderSettingsUI:
    def setup_method(self):
        import tempfile
        self.db_path = tempfile.mktemp(suffix=".db")
        from utils.database import DatabaseManager
        self.db = DatabaseManager(db_path=self.db_path)

    def teardown_method(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_ai_provider_button_shows_gemini_by_default(self):
        ai_provider = self.db.get_setting("ai_provider", "GEMINI")
        assert ai_provider == "GEMINI"

    def test_ai_provider_button_shows_claude_after_switch(self):
        self.db.set_setting("ai_provider", "CLAUDE")
        ai_provider = self.db.get_setting("ai_provider", "GEMINI")
        assert ai_provider == "CLAUDE"

    def test_toggle_gemini_to_claude(self):
        current = self.db.get_setting("ai_provider", "GEMINI")
        new_val = "CLAUDE" if current == "GEMINI" else "GEMINI"
        self.db.set_setting("ai_provider", new_val)
        result = self.db.get_setting("ai_provider", "GEMINI")
        assert result == "CLAUDE"

    def test_toggle_claude_to_gemini(self):
        self.db.set_setting("ai_provider", "CLAUDE")
        current = self.db.get_setting("ai_provider", "GEMINI")
        new_val = "CLAUDE" if current == "GEMINI" else "GEMINI"
        self.db.set_setting("ai_provider", new_val)
        result = self.db.get_setting("ai_provider", "GEMINI")
        assert result == "GEMINI"


class TestFailSafeIntegration:
    @pytest.mark.asyncio
    async def test_bot_does_not_crash_on_claude_exception(self):
        from utils.ai_engine import AIEngine
        engine = AIEngine(api_keys=["fake-key"])
        engine.claude_api_key = "sk-ant-test"
        engine.claude_client = object()
        engine._get_claude_analysis = AsyncMock(side_effect=Exception("Crash"))
        engine._get_gemini_analysis = AsyncMock(return_value="Gemini rescue")
        try:
            result = await engine.get_analysis("test", provider="CLAUDE")
            assert isinstance(result, str)
        except Exception:
            pytest.fail("Bot qulab tushdi!")

    @pytest.mark.asyncio
    async def test_both_providers_fail_returns_error_string(self):
        from utils.ai_engine import AIEngine
        engine = AIEngine(api_keys=["fake-key"])
        engine.claude_api_key = "sk-ant-test"
        engine.claude_client = object()
        engine._get_claude_analysis = AsyncMock(side_effect=Exception("Claude down"))
        engine._get_gemini_analysis = AsyncMock(side_effect=Exception("Gemini down"))
        result = await engine.get_analysis("test", provider="CLAUDE")
        assert isinstance(result, str)
