import sqlite3
import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=None):
        if not db_path:
            db_path = os.getenv("DB_PATH", "logs/bot_data.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=30)

    def _execute_query(self, query, params=(), is_fetch=False):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if is_fetch:
                return cursor.fetchall()
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Database Query Error: {e}")
            return None
        finally:
            conn.close()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT, symbol TEXT, side TEXT,
                    entry REAL, result TEXT, r_gain REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY, value TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT, role TEXT, content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT, symbol TEXT, direction TEXT,
                    entry REAL, sl REAL, tp1 REAL,
                    quality INTEGER, reason TEXT,
                    result TEXT DEFAULT 'PENDING',
                    sig_hash TEXT,
                    realized_pnl REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Migratsiya: yetishmagan ustunlarni qo'shish
            for col_name, col_type in [
                ('sl',          'REAL'),
                ('tp1',         'REAL'),
                ('quality',     'INTEGER'),
                ('reason',      'TEXT'),
                ('result',      "TEXT DEFAULT 'PENDING'"),
                ('sig_hash',    'TEXT'),
                ('realized_pnl','REAL DEFAULT 0.0'),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.warning(f"Migratsiya ({col_name}): {e}")

            # ✅ SQLite INDEX — Migratsiyadan KEYIN (ustunlar tayyor bo'lganida)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sig_timestamp ON signals(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sig_symbol    ON signals(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sig_hash      ON signals(sig_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_symbol   ON history(symbol)")

            conn.commit()
            logger.info("SQLite Baza ✅ Tayyor: " + self.db_path)
        except Exception as e:
            logger.error(f"Baza yaratishda xato: {e}")
        finally:
            conn.close()

    # ── Signallar ──────────────────────────────────────────────────────────────
    def add_signal(self, time_str, symbol, direction, entry, sl, tp1, quality, reason, sig_hash=None):
        query = ("INSERT INTO signals "
                 "(time, symbol, direction, entry, sl, tp1, quality, reason, sig_hash) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
        self._execute_query(query, (time_str, symbol, direction.upper(), entry, sl, tp1, quality, reason, sig_hash))

    def get_pending_signals(self):
        query = "SELECT id, symbol, direction, entry, sl, tp1, timestamp FROM signals WHERE result = 'PENDING'"
        return self._execute_query(query, (), is_fetch=True)

    def update_signal_result(self, sig_id, result):
        query = "UPDATE signals SET result = ? WHERE id = ?"
        self._execute_query(query, (result, sig_id))

    def mark_signal_result(self, sig_hash: str, result: str):
        """
        Sprint 2: TP/SL/Skip natijasini sig_hash orqali belgilash.
        result: 'tp' | 'sl' | 'skip'
        """
        result_map = {'tp': 'WIN', 'sl': 'LOSS', 'skip': 'SKIP'}
        db_result = result_map.get(result.lower(), result.upper())
        # realized_pnl ni ham yangilaymiz (taxminiy: WIN=+2R, LOSS=-1R)
        pnl = 2.0 if db_result == 'WIN' else (-1.0 if db_result == 'LOSS' else 0.0)
        query = "UPDATE signals SET result = ?, realized_pnl = ? WHERE sig_hash = ?"
        self._execute_query(query, (db_result, pnl, sig_hash))
        # history jadvaliga ham yozamiz
        rows = self._execute_query(
            "SELECT symbol, direction, entry FROM signals WHERE sig_hash = ?",
            (sig_hash,), is_fetch=True)
        if rows:
            sym, direction, entry = rows[0]
            self.add_history(
                datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
                sym, direction == 'BUY', entry, db_result, pnl
            )

    # ── Sprint 2: Bugungi signallar ────────────────────────────────────────────
    def get_today_signals(self) -> list:
        """Bugungi UTC kun ichida yuborilgan barcha signallar."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        query = ("SELECT time, symbol, direction, entry, sl, tp1, quality, result "
                 "FROM signals WHERE time LIKE ? ORDER BY id DESC")
        rows = self._execute_query(query, (f"{today}%",), is_fetch=True)
        if not rows:
            return []
        return [{'time': r[0], 'symbol': r[1], 'direction': r[2],
                 'entry': r[3], 'sl': r[4], 'tp1': r[5],
                 'quality': r[6], 'result': r[7]} for r in rows]

    # ── Sprint 2: Oylik va haftalik P&L ────────────────────────────────────────
    def get_period_pnl(self, days: int = 30) -> dict:
        """
        Sprint 2: Belgilangan kun oralig'i uchun P&L hisoboti.
        days=1 → bugun, days=7 → haftalik, days=30 → oylik
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
        query = ("SELECT result, realized_pnl FROM signals "
                 "WHERE timestamp >= ? AND result != 'PENDING'")
        rows = self._execute_query(query, (cutoff,), is_fetch=True) or []

        tp = sl = skip = 0
        total_r = 0.0
        for row in rows:
            res = str(row[0]).upper()
            pnl = float(row[1] or 0)
            if res == 'WIN':   tp += 1
            elif res == 'LOSS': sl += 1
            elif res == 'SKIP': skip += 1
            total_r += pnl

        total = tp + sl
        winrate = round(tp / total * 100, 1) if total > 0 else 0.0
        return {
            'days': days, 'tp': tp, 'sl': sl, 'skip': skip,
            'total': total, 'winrate': winrate,
            'total_r': round(total_r, 2)
        }

    # ── Tarix ──────────────────────────────────────────────────────────────────
    def add_history(self, time_str, symbol, is_buy, entry, result, r_gain):
        side = 'BUY' if is_buy else 'SELL'
        query = "INSERT INTO history (time, symbol, side, entry, result, r_gain) VALUES (?, ?, ?, ?, ?, ?)"
        self._execute_query(query, (time_str, symbol, side, entry, result, r_gain))

    def get_history(self, limit=100):
        query = 'SELECT time, symbol, side, entry, result, r_gain FROM history ORDER BY id DESC LIMIT ?'
        rows = self._execute_query(query, (limit,), is_fetch=True)
        if not rows: return []
        return [{'time': r[0], 'symbol': r[1], 'buy': r[2] == 'BUY',
                 'entry': r[3], 'result': r[4], 'r': r[5]} for r in rows]

    # ── Chat tarixi ────────────────────────────────────────────────────────────
    def add_chat_message(self, user_id, role, content, max_history=15):
        uid_str = str(user_id)
        self._execute_query(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (uid_str, role, content))
        self._execute_query('''
            DELETE FROM chat_history
            WHERE id IN (
                SELECT id FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC LIMIT -1 OFFSET ?
            )''', (uid_str, max_history))

    def get_chat_history(self, user_id, limit=15):
        query = 'SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id ASC LIMIT ?'
        rows = self._execute_query(query, (str(user_id), limit), is_fetch=True)
        if not rows: return []
        return [{'role': r[0], 'content': r[1]} for r in rows]

    # ── Statistika ─────────────────────────────────────────────────────────────
    def get_stats(self, hours=None, limit=100):
        time_filter = ""
        params_hist = [limit]
        if hours:
            time_filter = " WHERE timestamp >= datetime('now', '-%d hours') " % hours
        query_hist = f"SELECT result, r_gain FROM history {time_filter} ORDER BY id DESC LIMIT ?"
        rows_hist = self._execute_query(query_hist, params_hist, is_fetch=True)
        query_sigs = f"SELECT COUNT(*) FROM signals {time_filter}"
        rows_sigs = self._execute_query(query_sigs, (), is_fetch=True)
        total_signals = rows_sigs[0][0] if rows_sigs else 0
        tp = sl = 0; total_r = 0.0
        if not rows_hist:
            return {"tp": 0, "sl": 0, "winrate": 0, "profit": 0.0,
                    "total": 0, "total_signals": total_signals}
        for r in rows_hist:
            res = str(r[0]).upper()
            gain = float(r[1] or 0)
            if 'TP' in res or 'PROFIT' in res or 'WIN' in res: tp += 1
            elif 'SL' in res or 'LOSS' in res: sl += 1
            total_r += gain
        total = tp + sl
        winrate = round((tp / total * 100), 1) if total > 0 else 0
        return {"tp": tp, "sl": sl, "winrate": winrate,
                "profit": round(total_r, 2), "total": total,
                "total_signals": total_signals}

    def clear_all_stats(self):
        self._execute_query("DELETE FROM signals")
        self._execute_query("DELETE FROM history")
        return True
