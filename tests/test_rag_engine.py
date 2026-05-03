import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.rag_engine import RAGEngine

class TestRAGEngine:
    @patch('utils.rag_engine.genai.Client')
    def test_rag_engine_initialization(self, mock_client):
        # Mock client initialization
        engine = RAGEngine(api_keys="test_key")
        assert engine is not None
        assert engine.keys == ["test_key"]

    def test_chunk_text(self):
        engine = RAGEngine(api_keys="test_key")
        text = "Bu juda uzun matn bo'lib, uni bir nechta bo'laklarga ajratish kerak. " * 20
        chunks = engine.chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    @pytest.mark.asyncio
    @patch('utils.rag_engine.genai.Client')
    async def test_build_index(self, mock_client_class):
        mock_client = mock_client_class.return_value
        # Mock embedding response
        mock_emb = MagicMock()
        mock_emb.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        mock_client.models.embed_content.return_value = mock_emb
        
        # Create temp files
        os.makedirs("test_kb", exist_ok=True)
        with open("test_kb/test.txt", "w", encoding="utf-8") as f:
            f.write("Salom, bu test ma'lumoti. Bu matn etarli darajada uzun bo'lishi kerakki, RAG engine uni qabul qilsin.")
            
        engine = RAGEngine(api_keys="test_key", k_base_dir="test_kb", index_file="test_index.json")
        count = await engine.build_index(force=True)
        
        assert count > 0
        assert len(engine.documents) > 0
        assert len(engine.embeddings) > 0
        
        # Cleanup
        if os.path.exists("test_kb/test.txt"): os.remove("test_kb/test.txt")
        if os.path.exists("test_index.json"): os.remove("test_index.json")

    @patch('utils.rag_engine.genai.Client')
    def test_search(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_emb = MagicMock()
        mock_emb.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        mock_client.models.embed_content.return_value = mock_emb
        
        engine = RAGEngine(api_keys="test_key")
        engine.documents = ["Salom dunyo", "Test xabari"]
        engine.embeddings = [np.array([0.1, 0.2, 0.3]), np.array([0.9, 0.8, 0.7])]
        
        results = engine.search("Salom")
        assert "Salom dunyo" in results
