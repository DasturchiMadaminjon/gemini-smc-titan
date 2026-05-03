import asyncio
import yaml
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def start_indexing():
    try:
        with open('config/settings.yaml', 'r') as f:
            yaml_content = os.path.expandvars(f.read())
            cfg = yaml.safe_load(yaml_content)
            keys = cfg.get('gemini_ai', {}).get('api_keys', [])
            
            # Agar settings ichida string ko'rinishida bo'lsa
            if isinstance(keys, str):
                keys = [keys]
            
            # Yana bir fallback - to'g'ridan to'g'ri .env dan o'qish
            if not keys or not keys[0] or keys[0].startswith('$'):
                env_key = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY_1') or os.getenv('GOOGLE_API_KEY')
                if env_key:
                    # Vergul bilan ajratilgan kalitlarni massivga aylantirish
                    keys = [k.strip() for k in env_key.split(',') if len(k.strip()) > 20]
        
        if not keys or not keys[0]:
            print("❌ .env faylidan API kalit (GEMINI_API_KEY) o'qilmadi! Iltimos .env faylingiz to'g'riligini tekshiring.")
            return

        from utils.rag_engine import RAGEngine
        rag = RAGEngine(keys)
        
        print("\n⏳ 44 MB hajmli kitoblarni qismlarga bo'lish va Vektorlashtirish boshlanmoqda...")
        print("Bu jarayon kitob hajmiga va internetga qarab 2-5 daqiqa ketishi mumkin.")
        
        total_chunks = await rag.build_index()
        print(f"\n✅ TABRIKLAMIZ! Barcha kitoblar sun'iy intellekt xotirasiga {total_chunks} ta vektor qism sifatida muhrlandi!")
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    asyncio.run(start_indexing())
