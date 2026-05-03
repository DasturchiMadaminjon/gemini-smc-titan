import asyncio
import yaml
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def start_indexing():
    try:
        from utils.rag_engine import RAGEngine
        # RAGEngine o'zi .env dan kalitlarni oladi
        rag = RAGEngine()
        
        print("\n🚀 [MASTER ENGINE] Bilimlar bazasini indeksatsiya qilish boshlanmoqda...")
        print("Bu jarayon kitoblar hajmiga qarab biroz vaqt olishi mumkin...")
        
        total_chunks = await rag.build_index(force=True)
        print(f"\n[OK] Muvaffaqiyatli! {total_chunks} ta vektor qism xotiraga muhrlandi.")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

if __name__ == "__main__":
    asyncio.run(start_indexing())
