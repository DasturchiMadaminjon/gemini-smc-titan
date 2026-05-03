import asyncio
from google import genai
from google.genai import types

async def test():
    key = "AIzaSyAkProD9opDW7B2dupOc3xafbxbKpe1wvw"
    client = genai.Client(api_key=key)
    model = "models/gemini-2.5-flash"
    
    print(f"--- Final Test: {model} ---")
    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
        )
        resp = client.models.generate_content(
            model=model, 
            contents="Bugun 2026-yil 3-may. Dunyoda nima yangiliklar? (Google Search ishlat)",
            config=config
        )
        print("✅ Google Search: OK")
        print(f"AI: {resp.text[:200]}...")
    except Exception as e:
        print(f"❌ XATO: {e}")

if __name__ == "__main__":
    asyncio.run(test())
