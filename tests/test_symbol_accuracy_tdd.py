import pytest
from utils.exchange import ExchangeClient, _to_yahoo

@pytest.mark.asyncio
async def test_xauusd_gold_price_range():
    """
    TDD: XAU/USD (Gold) tickerining narxi Oltin diapazonida ekanligini tekshirish.
    S&P 500 (4700+) bilan adashib ketmasligi kerak.
    """
    client = ExchangeClient({})
    # 1. Ticker o'girilishini tekshirish
    ticker = _to_yahoo("XAU/USD")
    assert ticker == "GC=F", "XAU/USD ticker xato map qilingan!"
    
    # 2. Real narxni olish (yfinance orqali)
    df = await client.fetch_ohlcv("XAU/USD", "1d", limit=1)
    assert df is not None, "Oltin narxini olib bo'lmadi!"
    
    price = df['close'].iloc[-1]
    print(f"DEBUG: Current Gold Price = {price}")
    
    # Oltin narxi mantiqan 1000 dan baland va 3500 dan past bo'lishi kerak (2026-yilda)
    # S&P 500 esa 4500+ atrofida.
    assert 1500 < price < 3500, f"KRITIK XATO: XAU/USD narxi ({price}) Oltin diapazonida emas! Balki boshqa instrument (SPX?) ma'lumotlari kelyapti."

def test_symbol_mapping_normalization():
    """
    TDD: Simvollar registrga sezgir emasligini tekshirish.
    """
    assert _to_yahoo("xau/usd") == "GC=F"
    assert _to_yahoo("btc/usdt") == "BTC-USD"
    assert _to_yahoo("XAU/USD ") == "GC=F" # Probel bilan ham ishlashi kerak

@pytest.mark.asyncio
async def test_btc_price_range():
    """
    TDD: BTC/USDT narxi mantiqiy diapazonda ekanligini tekshirish.
    """
    client = ExchangeClient({})
    df = await client.fetch_ohlcv("BTC/USDT", "1d", limit=1)
    assert df is not None
    price = df['close'].iloc[-1]
    assert price > 10000, f"BTC narxi juda past: {price}"
