import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Inject fake fitz module into sys.modules to avoid ModuleNotFoundError on machines without fitz installed
mock_fitz = MagicMock()
sys.modules['fitz'] = mock_fitz

import pytest
import os
import json
import threading
from utils.telegram import TelegramNotifier

class TestPageRenderingTDD:
    """TDD test cases for PDF page rendering (/sahifa and /page commands)"""

    @pytest.mark.asyncio
    @patch('utils.telegram.DatabaseManager')
    async def test_sahifa_command_parsing_and_rendering(self, mock_db_cls):
        # Arrange
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_setting.return_value = "PUBLIC"
        mock_db.get_user_status.return_value = "ACTIVE"
        
        cfg = {
            'telegram': {'bot_token': '123:abc', 'chat_id': ['123']},
            'gemini_ai': {'api_keys': ['key1'], 'model': 'models/gemini-2.5-flash'}
        }
        
        notifier = TelegramNotifier(cfg, threading.Lock())
        notifier.send_photo = AsyncMock(return_value=True)
        notifier.send = AsyncMock(return_value=True)
        
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        
        mock_doc.__len__.return_value = 100
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        
        mock_fitz.open.return_value = mock_doc
        
        with patch('os.listdir', return_value=["SMC (TRADING DARSLIKLAR).pdf", "FIBO STRATEGY TEXO TRADE.pdf"]), \
             patch('os.path.exists', return_value=True):
            
            # Act: update message with /sahifa command
            u = {
                'update_id': 1001,
                'message': {
                    'from': {'id': '123', 'username': 'testuser'},
                    'text': '/sahifa 15 fibo'
                }
            }
            bs = {'symbols': {}, 'ai_requests': []}
            cfg_full = {'symbols': ['XAU/USD']}
            sess = MagicMock()
            
            off = await notifier.handle_update(u, bs, cfg_full, sess, ".tg_offset_test")
            
            # Assert
            assert off == 1001
            mock_fitz.open.assert_called_once_with(os.path.join("bilim_bazasi", "FIBO STRATEGY TEXO TRADE.pdf"))
            mock_doc.load_page.assert_called_once_with(14) # 15-1 = 14
            notifier.send_photo.assert_called_once()
            
            # Verify the args of send_photo
            call_kwargs = notifier.send_photo.call_args[1]
            assert call_kwargs['photo'] == b"fake_png_bytes"
            assert "15" in call_kwargs['caption']
            assert "FIBO STRATEGY" in call_kwargs['caption']
        
        # Reset mock
        mock_fitz.open.reset_mock()

    @pytest.mark.asyncio
    @patch('utils.telegram.DatabaseManager')
    async def test_sahifa_command_default_book(self, mock_db_cls):
        # Arrange
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_setting.return_value = "PUBLIC"
        mock_db.get_user_status.return_value = "ACTIVE"
        
        cfg = {
            'telegram': {'bot_token': '123:abc', 'chat_id': ['123']},
            'gemini_ai': {'api_keys': ['key1'], 'model': 'models/gemini-2.5-flash'}
        }
        
        notifier = TelegramNotifier(cfg, threading.Lock())
        notifier.send_photo = AsyncMock(return_value=True)
        notifier.send = AsyncMock(return_value=True)
        
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        
        mock_doc.__len__.return_value = 100
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.tobytes.return_value = b"fake_png_bytes"
        
        mock_fitz.open.return_value = mock_doc
        
        with patch('os.listdir', return_value=["SMC (TRADING DARSLIKLAR).pdf", "FIBO STRATEGY TEXO TRADE.pdf"]), \
             patch('os.path.exists', return_value=True):
            
            # Act: update message with /sahifa command without keyword
            u = {
                'update_id': 1002,
                'message': {
                    'from': {'id': '123', 'username': 'testuser'},
                    'text': '/sahifa 15'
                }
            }
            bs = {'symbols': {}, 'ai_requests': []}
            cfg_full = {'symbols': ['XAU/USD']}
            sess = MagicMock()
            
            off = await notifier.handle_update(u, bs, cfg_full, sess, ".tg_offset_test")
            
            # Assert
            assert off == 1002
            mock_fitz.open.assert_called_once_with(os.path.join("bilim_bazasi", "SMC (TRADING DARSLIKLAR).pdf"))
        
        # Reset mock
        mock_fitz.open.reset_mock()
