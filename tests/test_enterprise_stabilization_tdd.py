import pytest
from utils.position_sizer import calculate_position, format_position_line

def test_crypto_sl_formatting():
    """
    TDD: Kripto juftliklarida SL masofasi pip emas, 
    balki USD va foizda chiqishini tekshirish.
    """
    # SOL/USDT misolida (Narx ~140, SL 5$ masofada)
    balance = 1000.0
    risk_pct = 2.0
    entry = 145.0
    sl = 140.0
    symbol = "SOL/USDT"
    
    # 1. Hisoblashni tekshirish
    res = calculate_position(balance, risk_pct, entry, sl, symbol)
    assert res['is_crypto'] is True
    assert res['sl_delta'] == 5.0
    assert res['sl_perc'] == round((5/145)*100, 2)
    
    # 2. Matn formatini tekshirish
    line = format_position_line(balance, risk_pct, entry, sl, 160.0, 180.0, symbol)
    assert "$" in line
    assert "%" in line
    assert "pip" not in line.lower()
    print(f"DEBUG Crypto Line: {line}")

def test_forex_sl_formatting():
    """
    TDD: Forexda SL masofasi hamon 'pip' ko'rinishida qolishini tekshirish.
    """
    balance = 1000.0
    risk_pct = 2.0
    entry = 1.0850
    sl = 1.0800
    symbol = "EUR/USD"
    
    line = format_position_line(balance, risk_pct, entry, sl, 1.0950, 1.1000, symbol)
    assert "pip" in line.lower()
    assert "50 pip" in line
    print(f"DEBUG Forex Line: {line}")

@pytest.mark.asyncio
async def test_ai_truncation_config():
    """
    TDD: AI Engine konfiguratsiyasida max_output_tokens va 
    to'liq javob buyrug'i borligini tekshirish.
    """
    from utils.ai_engine import AIEngine
    import os
    
    # Fake API key bilan engine yaratish
    engine = AIEngine("fake_key")
    
    # Biz get_analysis ichidagi generation_config ni mock orqali tekshirishimiz mumkin
    # Lekin hozir personas dagi 'technical' instruksiyasini tekshiramiz
    persona = engine.personas.get("technical", "")
    assert "oxirigacha" in persona.lower() or "yakunlab" in persona.lower()
