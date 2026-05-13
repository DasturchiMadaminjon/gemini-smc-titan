from utils.ai_engine import AIEngine
import asyncio

async def main():
    ai = AIEngine()
    prompt = """
    Taqdim etilgan grafikni SMC prinsiplari asosida tahlil qiling va savdo bo'yicha maslahatlar bering.
    
    1. Struktura (BOS, CHoCH)
    2. Likvidlik
    3. Order Block (OB) va FVG
    """
    res = await ai.get_analysis(prompt, 'chat')
    print(f"LEN: {len(res)}")
    print("RESPONSE: ")
    print(res)

if __name__ == '__main__':
    asyncio.run(main())
