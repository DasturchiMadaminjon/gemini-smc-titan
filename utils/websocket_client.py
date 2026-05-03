import asyncio
import json
import logging
import threading
import websockets
from typing import List, Dict, Callable

logger = logging.getLogger('GeminiBot.WebSocket')

class BinanceWS:
    """Binance real-time price stream manager"""
    def __init__(self, symbols: List[str], callback: Callable[[str, float], None]):
        self.symbols = [s.lower().replace('/', '').replace('usdt', 'usdt') for s in symbols if 'USDT' in s]
        self.callback = callback
        self._stop_event = asyncio.Event()
        self._thread = None
        self._loop = None

    async def _listen(self):
        """Websocket ulanishi va ma'lumotlarni qabul qilish"""
        if not self.symbols:
            logger.info("Binance WS uchun simvollar topilmadi (faqat USDT juftliklari qo'llab-quvvatlanadi)")
            return

        streams = "/".join([f"{s}@ticker" for s in self.symbols])
        url = f"wss://stream.binance.com:9443/ws/{streams}"

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Binance WS ulandi: {len(self.symbols)} simvol kutilmoqda...")
                    while not self._stop_event.is_set():
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        # Binance ticker format: s=symbol, c=last_price
                        symbol = data.get('s', '').upper()
                        # Bot formatiga qaytarish (BTCUSDT -> BTC/USDT)
                        if symbol.endswith('USDT'):
                            bot_symbol = symbol.replace('USDT', '/USDT')
                        else:
                            bot_symbol = symbol

                        price = float(data.get('c', 0))
                        self.callback(bot_symbol, price)

            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"Binance WS xatosi: {e}. 5 soniyadan keyin qayta ulanadi...")
                    await asyncio.sleep(5)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._listen())

    def start(self):
        """WS stramni alohida threadda ishga tushirish"""
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
