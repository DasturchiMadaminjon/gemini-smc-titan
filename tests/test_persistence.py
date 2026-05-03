"""
tests/test_persistence.py
Bot state saqlash va yuklash logikasini tekshirish.
"""
import pytest
import os
import json
import tempfile
from unittest.mock import patch


class TestPersistence:
    """Persistence moduli uchun testlar"""

    def test_save_and_load_state(self, tmp_path):
        """State faylga yozib, qayta o'qish ishlaydi."""
        state_file = str(tmp_path / "bot_state.json")

        with patch("utils.persistence.STATE_FILE", state_file):
            from utils.persistence import save_state, load_state

            test_state = {
                "symbols": {"XAU/USD": {"price": 2350.0}},
                "terminal": {"balance": 5000.0},
                "ai_requests": [],
                "loss_streak": 2
            }
            save_state(test_state)
            loaded = load_state()

        assert loaded is not None
        assert loaded["terminal"]["balance"] == 5000.0
        assert loaded["symbols"]["XAU/USD"]["price"] == 2350.0
        assert loaded["loss_streak"] == 2

    def test_load_state_when_file_missing(self, tmp_path):
        """Fayl yo'q bo'lsa None qaytadi."""
        nonexistent = str(tmp_path / "nonexistent.json")
        with patch("utils.persistence.STATE_FILE", nonexistent):
            from utils.persistence import load_state
            result = load_state()
        assert result is None

    def test_save_state_creates_directory(self, tmp_path):
        """data/ papkasi yo'q bo'lsa, u yaratiladi."""
        state_file = str(tmp_path / "new_dir" / "bot_state.json")
        with patch("utils.persistence.STATE_FILE", state_file):
            from utils.persistence import save_state
            save_state({"test": True})
        assert os.path.exists(state_file)

    def test_save_state_overwrites_existing(self, tmp_path):
        """Eski state yangi bilan almashtiriladi."""
        state_file = str(tmp_path / "bot_state.json")
        with patch("utils.persistence.STATE_FILE", state_file):
            from utils.persistence import save_state, load_state
            save_state({"balance": 1000.0})
            save_state({"balance": 9999.0})
            result = load_state()
        assert result["balance"] == 9999.0

    def test_load_state_invalid_json(self, tmp_path):
        """Buzilgan JSON faylda None qaytadi."""
        state_file = str(tmp_path / "bot_state.json")
        os.makedirs(tmp_path, exist_ok=True)
        with open(state_file, 'w') as f:
            f.write("INVALID JSON {{{")
        with patch("utils.persistence.STATE_FILE", state_file):
            from utils.persistence import load_state
            result = load_state()
        assert result is None
