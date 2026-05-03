"""
GEMINI SMC TITAN V27.2 — Position Sizer
Balans va SL asosida optimal lot/coin miqdorini hisoblash.
Risk qoidasi: Har bir bitimda kapitalning max 2% si xavf ostida.
"""

# Har bir instrument uchun 1 ta birlik (lot/coin) harakat qiymatining USD'dagi qiymati
# Forex: 1 standart lot = 100,000 birlik; 1 pip = $10
# Gold: 1 standart lot = 100 oz; 1 pip = $1
# Crypto: 1 birlik = 1 coin (to'g'ridan-to'g'ri narx farqi)
INSTRUMENT_SPECS = {
    # GOLD
    'XAU/USD':  {'pip_size': 0.01, 'pip_value_per_lot': 1.0,  'min_lot': 0.01, 'unit': 'Lot'},
    'GOLD':     {'pip_size': 0.01, 'pip_value_per_lot': 1.0,  'min_lot': 0.01, 'unit': 'Lot'},
    # Major Forex
    'EUR/USD':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'GBP/USD':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'AUD/USD':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'NZD/USD':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'USD/CHF':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'USD/CAD':  {'pip_size': 0.0001, 'pip_value_per_lot': 10.0, 'min_lot': 0.01, 'unit': 'Lot'},
    'USD/JPY':  {'pip_size': 0.01,   'pip_value_per_lot': 9.1,  'min_lot': 0.01, 'unit': 'Lot'},
    # Crypto (to'g'ridan-to'g'ri)
    'BTC/USDT': {'pip_size': 1.0, 'pip_value_per_lot': 1.0, 'min_lot': 0.001, 'unit': 'BTC'},
    'ETH/USDT': {'pip_size': 1.0, 'pip_value_per_lot': 1.0, 'min_lot': 0.01,  'unit': 'ETH'},
    'XRP/USDT': {'pip_size': 0.0001, 'pip_value_per_lot': 1.0, 'min_lot': 1.0, 'unit': 'XRP'},
}

def calculate_position(balance: float, risk_pct: float,
                       entry: float, sl: float, symbol: str) -> dict:
    """
    Kapital va SL asosida optimal pozitsiya hajmini hisoblash.

    Returns:
        dict: {
            'risk_dollar': float,   # Xavf ostidagi dollar miqdori
            'sl_pips': float,       # SL masofasi (pip/birlik)
            'lot_size': float,      # Tavsiya etilgan lot hajmi
            'unit': str,            # Birlik nomi (Lot, BTC, ETH...)
            'rr': str,              # Risk:Reward nisbati (masalan "1:2")
        }
    """
    spec = INSTRUMENT_SPECS.get(symbol.upper(), INSTRUMENT_SPECS.get('EUR/USD'))

    risk_dollar   = round(balance * risk_pct / 100, 2)
    sl_distance   = abs(entry - sl)

    if sl_distance == 0 or entry == 0:
        return {'risk_dollar': risk_dollar, 'sl_pips': 0, 'lot_size': 0.0, 'unit': spec['unit']}

    # Pip soni
    sl_pips = sl_distance / spec['pip_size']

    # Lot = Xavf $ / (Pip soni × Bir Lot Pip Qiymati)
    lot_size = risk_dollar / (sl_pips * spec['pip_value_per_lot'])

    # Minimum lot chegarasi
    lot_size = max(spec['min_lot'], round(lot_size, 2))

    return {
        'risk_dollar': risk_dollar,
        'sl_pips':     round(sl_pips, 1),
        'lot_size':    lot_size,
        'unit':        spec['unit'],
    }


def format_position_line(balance: float, risk_pct: float,
                         entry: float, sl: float, tp1: float,
                         tp2: float, symbol: str) -> str:
    """Signal xabariga qo'shish uchun tayyor qator."""
    d = calculate_position(balance, risk_pct, entry, sl, symbol)
    if d['lot_size'] == 0:
        return f"💰 Risk: ${d['risk_dollar']:.0f} ({risk_pct}%)"

    rr1 = abs(tp1 - entry) / abs(sl - entry) if abs(sl - entry) else 0
    rr2 = abs(tp2 - entry) / abs(sl - entry) if abs(sl - entry) else 0

    return (
        f"💰 <b>Position Sizing:</b>\n"
        f"   ├ Risk: <code>${d['risk_dollar']:.0f} ({risk_pct}%)</code>\n"
        f"   ├ SL masofa: <code>{d['sl_pips']:.0f} pip</code>\n"
        f"   ├ Hajm: <code>{d['lot_size']} {d['unit']}</code>\n"
        f"   └ R:R → TP1: <code>1:{rr1:.1f}</code> | TP2: <code>1:{rr2:.1f}</code>"
    )
