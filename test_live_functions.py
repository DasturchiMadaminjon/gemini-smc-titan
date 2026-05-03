import asyncio
import yaml
from utils.telegram import TelegramNotifier
from utils.news import NewsWatcher
import threading

async def main():
    print("--- LIVE TEST BOSHLANDI ---")
    
    # 1. Config yuklash
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    lock = threading.Lock()
    
    # 2. Telegram test
    print("1. Telegram modulini tekshirish...")
    telegram = TelegramNotifier(config, lock)
    try:
        # Adminlarga sinov xabari jo'natish
        await telegram.send("TEST: Telegram moduli va internet aloqasi to'g'ri ishlamoqda!")
        print("Telegram xabari muvaffaqiyatli yuborildi.")
    except Exception as e:
        print(f"Telegram xatosi: {e}")
        
    # 3. News test
    print("\n2. Yangiliklar (NewsWatcher) modulini tekshirish...")
    news = NewsWatcher(config)
    try:
        data = await news.fetch_news()
        print(f"URL dan jami {len(data)} ta yangilik yuklab olindi.")
        if data:
            print(f"Bitta namunaviy yangilik: {data[0].get('country')} - {data[0].get('event')} ({data[0].get('impact')} impact)")
            
        upcoming = await news.check_upcoming_news()
        if upcoming:
            print(f"Kelgusi 1 soat ichida {len(upcoming)} ta HIGH impact yangilik bor!")
        else:
            print("Kelgusi 1 soat ichida 'High Impact' yangilik yo'q.")
    except Exception as e:
        print(f"Yangiliklar moduli xatosi: {e}")

if __name__ == "__main__":
    asyncio.run(main())
