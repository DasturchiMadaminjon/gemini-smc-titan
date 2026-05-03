import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.rag_engine import RAGEngine

class TestRAGEngine:
    @patch('utils.rag_engine.genai.GenerativeModel')
    def test_rag_engine_initialization(self, mock_genai):
        engine = RAGEngine(MagicMock())
        assert engine is not None
