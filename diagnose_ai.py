import os
import asyncio
from google import genai
from google.genai import types
import yaml
from dotenv import load_dotenv

load_dotenv()

async def test_model_capability(api_key, model_name):
    print(f"\n🔍 Sinov: {model_name} (Key: {api_key[:10]}...)")
    client = genai.Client(api_key=api_key)
    
    # 1. Oddiy tahlil testi
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents="Salom, o'zingni tanishtir."
        )
        print(f"✅ Oddiy tahlil: OK ({resp.text[:50]}...)")
    except Exception as e:
        print(f"❌ Oddiy tahlil: XATO ({e})")
        return

    # 2. Google Search (Internet) testi
    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
        )
        resp = client.models.generate_content(
            model=model_name,
            contents="Bugungi USD/UZB kursi qancha? (Google Search ishlat)",
            config=config
        )
        if hasattr(resp, 'candidates') and resp.candidates[0].grounding_metadata:
            print(f"✅ Google Search: OK (Internetdan ma'lumot olindi!)")
        else:
            print(f"⚠️ Google Search: Ishlamadi (Lekin xato bermadi)")
    except Exception as e:
        print(f"❌ Google Search: QO'LLAB-QUVVATLANMAYDI ({e})")

async def main():
    # API kalitlarni configdan o'qish
    try:
        with open('config/settings.yaml', 'r') as f:
            cfg = yaml.safe_load(f)
            keys = cfg.get('gemini_ai', {}).get('api_keys', [])
    except:
        keys = [os.getenv("GEMINI_API_KEY")]

    test_models = ["models/gemini-2.0-flash", "models/gemini-1.5-flash", "models/gemini-1.5-pro"]
    
    for key in keys:
        if not key: continue
        for model in test_models:
            await test_model_capability(key, model)

if __name__ == "__main__":
    asyncio.run(main())
