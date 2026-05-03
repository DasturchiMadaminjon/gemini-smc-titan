"""
GEMINI V20 BOT - MetaTrader 5 Signal Yuborish Moduli
XM va Exness brokerlariga faqat signal (pending order) yuborish
Haqiqiy savdo emas - faqat signal!
"""
import logging
import time
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# MT5 import - agar o'rnatilmagan bo'lsa ogohlantirish
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 kutubxonasi topilmadi. pip install MetaTrader5")


# MT5 symbol mapping (bot symbol -> MT5 symbol ismi)
MT5_SYMBOL_MAP = {
    'XAU/USD':   'XAUUSDm',    # GOLD (ba'zi brokerlarda XAUUSDm)
    'XAUUSD':    'XAUUSDm',
    'GOLD':      'XAUUSDm',
    'ETH/USDT':  'ETHUSDTm',
    'BTC/USDT':  'BTCUSDTm',
    'SOL/USDT':  'SOLUSDTm',
    'XRP/USDT':  'XRPUSDTm',
    'BNB/USDT':  'BNBUSDTm',
    'EUR/USD':   'EURUSDm',
    'GBP/USD':   'GBPUSDm',
}


class MT5SignalSender:
    """
    MetaTrader 5 orqali signal yuborish
    XM va Exness brokerlarida ishlaydi
    FAQAT SIGNAL - haqiqiy savdo emas!
    """

    def __init__(self, config: dict):
        self.cfg     = config.get('mt5', {})
        self.enabled = self.cfg.get('enabled', False) and MT5_AVAILABLE
        self._connected = False

        if self.enabled:
            self._connect()

    def _connect(self) -> bool:
        """MT5 ga ulanish (V27 Update)"""
        if not MT5_AVAILABLE:
            return False

        if not mt5.initialize():
            logger.error(f"MT5 initialize xato: {mt5.last_error()}")
            return False

        login    = self.cfg.get('login', 0)
        password = self.cfg.get('password', '')
        server   = self.cfg.get('server', '')

        if login and password and server:
            auth = mt5.login(login=login, password=password, server=server)
            if not auth:
                logger.error(f"MT5 login xato: {mt5.last_error()}")
                self._connected = False
                return False
            
            info = mt5.account_info()
            if info:
                logger.info(f"MT5 ✅ Ulandi: {info.name} ({info.server}) | Balans: {info.balance} {info.currency}")
        else:
            logger.info("MT5 initialize qilindi (Auth ma'lumotlari yo'q)")

        self._connected = True
        return True

    def _ensure_connection(self) -> bool:
        """Ulanish mavjudligini tekshirish va kerak bo'lsa qayta ulanish"""
        if not self._connected or not mt5.terminal_info():
            logger.info("MT5 ulanishi uzilgan, qayta ulanishga urinish...")
            return self._connect()
        return True

    def _get_filling_mode(self, symbol: str) -> int:
        """Broker qo'llab-quvvatlaydigan filling rejimini aniqlash"""
        si = mt5.symbol_info(symbol)
        if not si: return mt5.ORDER_FILLING_IOC
        
        # Filling mode flags
        f_flags = si.filling_mode
        if f_flags & mt5.SYMBOL_FILLING_FOK:
            return mt5.ORDER_FILLING_FOK
        elif f_flags & mt5.SYMBOL_FILLING_IOC:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_IOC

    def _get_mt5_symbol(self, symbol: str) -> Optional[str]:
        """Simvolni broker formatiga moslash (XAUUSD -> XAUUSDm kabi)"""
        if not self._ensure_connection(): return None
        
        # 1. To'g'ridan-to'g'ri mapdan qidirish
        mt5_sym = MT5_SYMBOL_MAP.get(symbol.upper(), symbol.replace('/', ''))
        
        # 2. Mavjudligini tekshirish
        for suffix in ['', 'm', '.', '.m', 'i', '#']:
            test_sym = mt5_sym + suffix
            info = mt5.symbol_info(test_sym)
            if info:
                mt5.symbol_select(test_sym, True)
                return test_sym
            
            # Suffixlarsiz ham tekshirish (agar mapda 'm' bo'lsa-yu brokerda bo'lmasa)
            if suffix == '' and 'm' in mt5_sym:
                test_alt = mt5_sym.replace('m', '')
                if mt5.symbol_info(test_alt):
                    mt5.symbol_select(test_alt, True)
                    return test_alt

        logger.warning(f"MT5 symbol topilmadi: {symbol}")
        return None

    def calculate_lot(self, symbol: str, risk_perc: float, entry: float, sl: float) -> float:
        """Balans va riskdan kelib chiqib lotni hisoblash"""
        if not self.enabled or not self._ensure_connection(): return 0.01

        mt5_sym = self._get_mt5_symbol(symbol)
        if not mt5_sym: return 0.01

        try:
            acc = mt5.account_info()
            si  = mt5.symbol_info(mt5_sym)
            if not acc or not si: return 0.01

            # 1. Risk miqdori (dollar hisobida)
            risk_usd = acc.equity * (risk_perc / 100)
            
            # 2. Stop loss masofasi (punktlarda emas, narxda)
            price_diff = abs(entry - sl)
            if price_diff == 0: return si.volume_min

            # 3. 1 lot uchun risk qiymati
            # Formula: (Narx Farqi / Tick Size) * Tick Value
            tick_size = si.trade_tick_size if si.trade_tick_size > 0 else 0.00001
            tick_val  = si.trade_tick_value if si.trade_tick_value > 0 else 1.0
            risk_per_lot = (price_diff / tick_size) * tick_val

            if risk_per_lot <= 0: return si.volume_min

            # 4. Lotni hisoblash
            raw_lot = risk_usd / risk_per_lot
            
            # 5. Lotni broker talablariga moslash (min, max, step)
            vol_step = si.volume_step if si.volume_step > 0 else 0.01
            lot = round(raw_lot / vol_step) * vol_step
            
            # Chegaralar
            lot = max(si.volume_min, min(si.volume_max, lot))
            
            logger.info(f"📊 Lot Hisoblandi ({mt5_sym}): Equity:${acc.equity:.2f} Risk:{risk_perc}% -> Lot:{lot:.2f}")
            return round(lot, 2)
        except Exception as e:
            logger.error(f"Lot hisoblashda xato: {e}")
            return 0.01

    def send_signal(self, symbol: str, direction: str,
                    entry: float, sl: float,
                    tp1: float, tp2: float, tp3: float,
                    volume: float = None,
                    comment: str = "GEMINI V27") -> bool:
        """MT5 Signal yuborish (Smarter V27)"""
        if not self.enabled: return False
        if not self._ensure_connection(): return False

        mt5_sym = self._get_mt5_symbol(symbol)
        if not mt5_sym: return False

        try:
            info = mt5.symbol_info(mt5_sym)
            if not info: return False

            digits = info.digits
            filling = self._get_filling_mode(mt5_sym)
            
            # Lotni aniqlash (Parametrdan yoki minimal)
            final_vol = volume if volume else info.volume_min
            final_vol = max(info.volume_min, min(info.volume_max, final_vol))

            # Order type
            if direction == 'buy':
                order_type = mt5.ORDER_TYPE_BUY if abs(entry - info.ask)/info.ask < 0.0005 else mt5.ORDER_TYPE_BUY_LIMIT
                price = info.ask if order_type == mt5.ORDER_TYPE_BUY else entry
            else:
                order_type = mt5.ORDER_TYPE_SELL if abs(entry - info.bid)/info.bid < 0.0005 else mt5.ORDER_TYPE_SELL_LIMIT
                price = info.bid if order_type == mt5.ORDER_TYPE_SELL else entry

            request = {
                "action": mt5.TRADE_ACTION_PENDING if "LIMIT" in str(order_type) or order_type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT] else mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_sym,
                "volume": final_vol,
                "type": order_type,
                "price": round(price, digits),
                "sl": round(sl, digits),
                "tp": round(tp3, digits),
                "deviation": 20,
                "magic": 202406,
                "comment": comment[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }

            # Market order bo'lsa actionni to'g'irlash
            if order_type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL]:
                request["action"] = mt5.TRADE_ACTION_DEAL

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ MT5 Signal: {direction.upper()} {mt5_sym} | Price: {price:.{digits}f}")
                return True
            else:
                logger.error(f"MT5 Xato [{result.retcode if result else 'N/A'}]: {result.comment if result else 'Response null'}")
                return False

        except Exception as e:
            logger.error(f"MT5 send_signal exception: {e}")
            return False

    def close_all_positions(self) -> dict:
        """Barcha ochiq pozitsiyalarni yopish (Panic Button)"""
        if not self.enabled or not self._ensure_connection():
            return {'ok': False, 'msg': 'MT5 ulanmagan'}
        
        try:
            positions = mt5.positions_get()
            if not positions:
                return {'ok': True, 'count': 0, 'msg': 'Ochiq pozitsiyalar yo\'q'}
            
            closed_count = 0
            for pos in positions:
                sym_info = mt5.symbol_info(pos.symbol)
                type_map = {mt5.POSITION_TYPE_BUY: mt5.ORDER_TYPE_SELL, mt5.POSITION_TYPE_SELL: mt5.ORDER_TYPE_BUY}
                price_field = 'bid' if pos.type == mt5.POSITION_TYPE_BUY else 'ask'
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": type_map[pos.type],
                    "position": pos.ticket,
                    "price": getattr(sym_info, price_field),
                    "deviation": 20,
                    "magic": 202406,
                    "comment": "Panic Close V27",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": self._get_filling_mode(pos.symbol),
                }
                res = mt5.order_send(request)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_count += 1
            
            # Pending orderlarni ham o'chirish
            orders = mt5.orders_get()
            if orders:
                for o in orders:
                    mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})

            return {'ok': True, 'count': closed_count, 'msg': f'{closed_count} ta pozitsiya yopildi'}
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    def get_terminal_summary(self) -> dict:
        """Terminal holati summarysi - V27 Enhanced"""
        is_conn = self.enabled and self._ensure_connection()
        
        if not is_conn:
            return {
                'balance': 0.0, 'equity': 0.0, 'margin': 0.0,
                'pnl': 0.0, 'open_count': 0, 'connected': False
            }
        
        try:
            acc = mt5.account_info()
            pos = mt5.positions_get()
            
            p_count = len(pos) if pos else 0
            floating_pnl = sum([p.profit for p in pos]) if pos else 0
            used_margin = acc.margin if acc else 0
            
            return {
                'balance': acc.balance if acc else 0,
                'equity': acc.equity if acc else 0,
                'margin': used_margin,
                'pnl': floating_pnl,
                'open_count': p_count,
                'connected': True
            }
        except Exception as e:
            logger.error(f"get_terminal_summary xatosi: {e}")
            return {
                'balance': 0.0, 'equity': 0.0, 'margin': 0.0,
                'pnl': 0.0, 'open_count': 0, 'connected': False
            }


    def close(self):
        if MT5_AVAILABLE: mt5.shutdown()
