import yfinance as yf
import logging

logger = logging.getLogger(__name__)

# Symbol mapping
SYMBOL_MAP = {
    'XAU/USD': 'GC=F',
    'XAUUSD': 'GC=F',
    'GOLD': 'GC=F',
    'XAG/USD': 'SI=F',
    'XAGUSD': 'SI=F',
    'SILVER': 'SI=F',
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD',
    'EUR/USD': 'EURUSD=X',
    'GBP/USD': 'GBPUSD=X'
}

def get_current_price(symbol: str) -> str:
    """
    Belgilangan instrument (masalan: XAUUSD, BTCUSDT, GOLD) uchun real vaqt rejimida narxni oladi.
    
    Args:
        symbol: Instrument nomi (XAUUSD, BTCUSDT, GOLD va hk.)
        
    Returns:
        Narx haqida ma'lumot (matn ko'rinishida)
    """
    try:
        query = symbol.upper().strip()
        yf_sym = SYMBOL_MAP.get(query, query)
        
        # Agar mappingda yo'q bo'lsa va /USD yoki /USDT bo'lsa, ticker formatiga o'tkazamiz
        if yf_sym == query:
            if '/' in query:
                yf_sym = query.replace('/', '-').replace('USDT', 'USD')
            elif query.endswith('USDT'):
                yf_sym = query.replace('USDT', '-USD')
        
        ticker = yf.Ticker(yf_sym)
        # fast_info yoki history orqali oxirgi narxni olamiz
        df = ticker.history(period='1d', interval='1m')
        
        if not df.empty:
            price = df['Close'].iloc[-1]
            return f"Hozirgi vaqtda {symbol} narxi: {price:.2f} USD."
        else:
            # Fallback for some tickers that don't support 1m history easily
            info = ticker.fast_info
            if 'last_price' in info:
                return f"Hozirgi vaqtda {symbol} narxi: {info['last_price']:.2f} USD."
            
        return f"Kechirasiz, {symbol} uchun real vaqt narxini topib bo'lmadi."
    except Exception as e:
        logger.error(f"Price fetch error for {symbol}: {e}")
        return f"Narxni olishda xatolik yuz berdi: {str(e)}"
