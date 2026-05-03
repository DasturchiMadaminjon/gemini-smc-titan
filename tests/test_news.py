"""
tests/test_news.py
NewsWatcher modulini tekshirish uchun testlar.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from utils.news import NewsWatcher

@pytest.fixture
def news_watcher():
    cfg = {"telegram": {"bot_token": "test"}}
    return NewsWatcher(cfg)

@pytest.mark.asyncio
async def test_fetch_news_mock(news_watcher):
    """fetch_news funksiyasi mock orqali tekshiriladi."""
    mock_data = [{"event": "Test News", "impact": "High", "date": "2026-04-27T12:00:00Z"}]
    
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        res = await news_watcher.fetch_news()
        assert len(res) == 1
        assert res[0]['event'] == "Test News"

@pytest.mark.asyncio
async def test_check_upcoming_news_logic(news_watcher):
    """Yaqin 60 minut ichidagi yangilikni aniqlash mantiqi."""
    # Hozirgi vaqtdan 30 minut keyingi vaqtni yaratamiz (ISO format)
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    
    mock_data = [
        {
            "event": "FOMC Meeting",
            "impact": "High",
            "country": "USD",
            "date": future_time
        },
        {
            "event": "Low impact news",
            "impact": "Low",
            "country": "EUR",
            "date": future_time
        }
    ]
    
    with patch.object(NewsWatcher, 'fetch_news', return_value=mock_data):
        upcoming = await news_watcher.check_upcoming_news()
        
        assert len(upcoming) == 1
        assert upcoming[0]['event'] == "FOMC Meeting"
        assert upcoming[0]['country'] == "USD"

@pytest.mark.asyncio
async def test_news_notified_cache(news_watcher):
    """Bir xil yangilik uchun qayta ogohlantirmaslikni tekshirish."""
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    mock_data = [{"event": "CPI", "impact": "High", "country": "USD", "date": future_time}]
    
    with patch.object(NewsWatcher, 'fetch_news', return_value=mock_data):
        # Birinchi marta
        first = await news_watcher.check_upcoming_news()
        assert len(first) == 1
        
        # Ikkinchi marta (cache ishlashi kerak)
        second = await news_watcher.check_upcoming_news()
        assert len(second) == 0

@pytest.mark.asyncio
async def test_old_news_ignored(news_watcher):
    """O'tib ketgan yangiliklarni mensimaslik."""
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    mock_data = [{"event": "Old News", "impact": "High", "country": "USD", "date": past_time}]
    
    with patch.object(NewsWatcher, 'fetch_news', return_value=mock_data):
        upcoming = await news_watcher.check_upcoming_news()
        assert len(upcoming) == 0
