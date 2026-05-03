import asyncio
from google import genai
from google.genai import types

async def test():
    key = "AIzaSyAkProD9opDW7B2dupOc3xafbxbKpe1wvw"
    client = genai.Client(api_key=key)
    models = ["models/gemini-2.0-flash", "models/gemini-1.5-flash"]
    
    for m in models:
        print(f"--- Testing {m} ---")
        try:
            # 1. Basic
            r1 = client.models.generate_content(model=m, contents="Salom")
            print(f"✅ Basic: OK")
            
            # 2. Search
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
            )
            r2 = client.models.generate_content(
                model=m, 
                contents="Google Search orqali hozirgi USD/UZB kursini top",
                config=config
            )
            print(f"✅ Google Search: OK")
        except Exception as e:
            print(f"❌ XATO: {e}")

if __name__ == "__main__":
    asyncio.run(test())
