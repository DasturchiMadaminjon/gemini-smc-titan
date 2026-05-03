import aiohttp
import asyncio
import os
from datetime import datetime, timezone

class NewsWatcher:
    def __init__(self, config):
        self.cfg = config
        self.news_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.last_notified = []

    async def fetch_news(self):
        proxy = "http://proxy.server:3128" if "PYTHONANYWHERE_DOMAIN" in os.environ else None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.news_url, proxy=proxy) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"DEBUG: News fetch error: {e}")
        return []

    async def check_upcoming_news(self):
        news_data = await self.fetch_news()
        upcoming = []
        now = datetime.now(timezone.utc)
        
        for item in news_data:
            # Faqat yuqori (High) impact yangiliklarni olamiz
            if item.get('impact') == 'High':
                try:
                    # JSON date format: "2026-04-27T08:30:00-04:00"
                    date_str = item.get('date')
                    if not date_str: continue
                    
                    # ISO formatini to'g'ri parse qilish
                    # Python 3.11+ da fromisoformat() barcha ISO formatlarni yaxshi taniydi
                    news_time = datetime.fromisoformat(date_str)
                    
                    # Agar vaqt zonasi yo'q bo'lsa, UTC deb hisoblaymiz
                    if news_time.tzinfo is None:
                        news_time = news_time.replace(tzinfo=timezone.utc)
                    
                    # Vaqt farqini hisoblaymiz (minutlarda)
                    diff = (news_time - now).total_seconds() / 60
                    
                    # Agar yangilik keyingi 60 daqiqa ichida bo'lsa:
                    if 0 <= diff <= 60:
                        event_id = f"{item.get('country')}_{item.get('event')}_{date_str}"
                        if event_id not in self.last_notified:
                            upcoming.append(item)
                            self.last_notified.append(event_id)
                            # Log tozalash (eski xabarlarni o'chirish)
                            if len(self.last_notified) > 50: self.last_notified.pop(0)
                except Exception as e:
                    continue
        
        return upcoming
