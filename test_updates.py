import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv('.env')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PROXY = None # "http://proxy.server:3128" if "PYTHONANYWHERE_DOMAIN" in os.environ else None

async def main():
    print(f"Bot token: {TOKEN[:10]}...")
    async with aiohttp.ClientSession() as sess:
        off = 0
        while True:
            try:
                async with sess.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={off+1}&timeout=30", proxy=PROXY) as r:
                    if r.status == 200:
                        data = await r.json()
                        for u in data.get("result", []):
                            off = u["update_id"]
                            print(f"\n--- RAW UPDATE {off} ---")
                            print(u)
                    else:
                        print(f"Error: {r.status} {await r.text()}")
            except Exception as e:
                print("Exception:", e)
            await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
