"""
tests/test_file_reading_tdd.py
==============================
PDF, Word, Excel, CSV va JSON fayllarni o'qish funksiyalarini TDD orqali tekshirish.
"""
import pytest
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

def make_notifier():
    from utils.telegram import TelegramNotifier
    cfg = {'telegram': {'bot_token': 'test', 'chat_id': ['123']}, 'smc': {}, 'trend': {}, 'symbols': ['BTC/USDT']}
    n = TelegramNotifier(cfg, MagicMock())
    n.send = AsyncMock()
    return n

def doc_update(fname, fid="fid123"):
    return {
        'update_id': 1,
        'message': {
            'chat': {'id': 123},
            'from': {'id': 123},
            'document': {'file_name': fname, 'file_id': fid}
        }
    }

async def run_file_test(notifier, update, file_bytes):
    bs = {'ai_requests': [], 'settings': {}}
    cfg = {'symbols': ['BTC/USDT']}
    notifier.user_states["123"] = "in_session"
    
    sess = MagicMock()
    # getFile mock
    mock_get_file = MagicMock()
    mock_get_file.status = 200
    mock_get_file.json = AsyncMock(return_value={'result': {'file_path': 'path/to/file'}})
    
    # download file mock
    mock_download = MagicMock()
    mock_download.status = 200
    mock_download.read = AsyncMock(return_value=file_bytes)
    
    mock_cm_get = MagicMock()
    mock_cm_get.__aenter__ = AsyncMock(side_effect=[mock_get_file, mock_download])
    mock_cm_get.__aexit__ = AsyncMock(return_value=False)
    sess.get = MagicMock(return_value=mock_cm_get)
    
    sess.post = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=MagicMock(status=200)), __aexit__=AsyncMock(return_value=False)))

    await notifier.handle_update(update, bs, cfg, sess, '.tg_offset')
    return notifier.send.call_args_list, bs

@pytest.mark.asyncio
async def test_pdf_reading_logic():
    """PDF fayl yuborilganda matn ajratilishi kerak."""
    n = make_notifier()
    # Fake PDF bytes (not a real PDF, but enough for mocking logic if we want, 
    # but here we test the real PyPDF2 integration)
    # Since we can't easily create a real PDF here without extra libs, we will mock PdfReader
    with patch('PyPDF2.PdfReader') as mock_reader:
        mock_instance = mock_reader.return_value
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "SMC Strategy PDF Content"
        mock_instance.pages = [mock_page]
        
        calls, bs = await run_file_test(n, doc_update("strategy.pdf"), b"%PDF-1.4 fake")
        
        texts = [c[0][0] for c in calls]
        assert any("strategy.pdf" in t for t in texts)
        assert any("SMC Strategy PDF Content" in r['text'] for r in bs['ai_requests'])

@pytest.mark.asyncio
async def test_csv_reading_logic():
    """CSV fayl yuborilganda pandas orqali o'qilishi kerak."""
    n = make_notifier()
    csv_bytes = b"symbol,price\nBTC,60000\nETH,3000"
    
    calls, bs = await run_file_test(n, doc_update("trades.csv"), csv_bytes)
    
    assert any("BTC" in r['text'] for r in bs['ai_requests'])
    assert any("60000" in r['text'] for r in bs['ai_requests'])

@pytest.mark.asyncio
async def test_json_reading_logic():
    """JSON fayl yuborilganda json.loads orqali o'qilishi kerak."""
    n = make_notifier()
    data = {"test": "value"}
    json_bytes = json.dumps(data).encode()
    
    calls, bs = await run_file_test(n, doc_update("data.json"), json_bytes)
    
    assert any('"test": "value"' in r['text'] for r in bs['ai_requests'])

@pytest.mark.asyncio
async def test_invalid_file_type():
    """Noma'lum fayl yuborilganda ogohlantirish berishi kerak."""
    n = make_notifier()
    calls, bs = await run_file_test(n, doc_update("virus.exe"), b"bad")
    
    texts = [c[0][0] for c in calls]
    assert any("Faqat .pdf, .docx, .csv, .json va .xlsx" in t for t in texts)
