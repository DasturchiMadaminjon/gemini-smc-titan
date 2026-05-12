import pytest
from utils.exchange import ExchangeClient, _to_yahoo

@pytest.mark.asyncio
async def test_xauusd_vs_spx_isolation():
    """
    TDD: XAU/USD (Gold) narxi S&P 500 (SPX) narxidan alohida ekanligini tekshirish.
    Oltin ~2300, SPX ~5000 atrofida. Ular adashib ketmasligi shart.
    """
    client = ExchangeClient({})
    
    # 1. Oltin narxini olish
    gold_df = await client.fetch_ohlcv("XAU/USD", "1d", limit=1)
    assert gold_df is not None, "Oltin ma'lumotlarini olib bo'lmadi"
    gold_price = gold_df['close'].iloc[-1]
    
    # 2. S&P 500 (yoki shunga o'xshash indeks) narxini olish (simulyatsiya uchun ^GSPC dan foydalanamiz)
    import yfinance as yf
    spx = yf.Ticker("^GSPC")
    spx_df = spx.history(period="1d")
    spx_price = spx_df['Close'].iloc[-1]
    
    print(f"DEBUG: Gold = {gold_price}, SPX = {spx_price}")
    
    # Oltin narxi SPX narxidan kamida 1000 birlikka farq qilishi kerak
    diff = abs(gold_price - spx_price)
    assert diff > 1000, f"KRITIK XATO: Oltin narxi ({gold_price}) SPX narxiga ({spx_price}) juda yaqin! Tikerlar adashgan bo'lishi mumkin."
    assert gold_price < 3500, f"Oltin narxi me'yordan baland: {gold_price}"

def test_symbol_mapping_integrity():
    """
    TDD: Oltin tikeri GC=F ga qat'iy bog'langanini tekshirish.
    """
    assert _to_yahoo("XAU/USD") == "GC=F"
    assert _to_yahoo("xau/usd") == "GC=F"
    assert _to_yahoo("GOLD") == "GC=F"

def test_ai_rounding_instruction_presence():
    """
    TDD: AI Engine instruksiyalarida yaxlitlash buyrug'i borligini tekshirish.
    """
    from utils.ai_engine import AIEngine
    engine = AIEngine("fake_key")
    persona = engine.personas.get("technical", "")
    
    assert "yaxlitlab" in persona or "round" in persona.lower()
    assert "4-5" in persona or "decimal" in persona.lower()
