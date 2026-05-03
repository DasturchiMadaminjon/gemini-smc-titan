import io
import pandas as pd
import mplfinance as mpf
import logging
import asyncio

logger = logging.getLogger(__name__)

def _generate_plot(df: pd.DataFrame) -> bytes:
    # DataFrame indeksini Datetime formatiga o'tkazish majburiy
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        df.index = pd.to_datetime(df.index)

    # Xotira buferi yaratish
    buf = io.BytesIO()

    # mplfinance sozlamalari (Dark mode, professional ko'rinish)
    mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', wick='inherit', volume='in')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)

    # Grafikni xotiraga chizish
    mpf.plot(
        df.tail(100), # Faqat oxirgi 100 ta sham
        type='candle',
        style=s,
        volume=True,
        tight_layout=True,
        figratio=(16, 9),
        figscale=1.2,
        savefig=dict(fname=buf, dpi=100, format='png', bbox_inches='tight')
    )
    
    buf.seek(0)
    return buf.getvalue()

async def generate_chart_buffer(df: pd.DataFrame) -> bytes:
    """
    OHLCV DataFrame'dan xotirada candlestick chart yaratadi.
    Gemini API uchun bytes qaytaradi.
    """
    try:
        loop = asyncio.get_event_loop()
        # Matplotlib bloklanishining oldini olish uchun alohida thread'da bajaramiz
        image_bytes = await loop.run_in_executor(None, _generate_plot, df)
        return image_bytes
    except Exception as e:
        logger.error(f"Chart generatsiyasida xatolik: {str(e)}")
        raise
