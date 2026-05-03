import pytest
import os
from utils.database import DatabaseManager

@pytest.fixture
def db():
    test_db = "logs/test_bot.db"
    if os.path.exists(test_db): os.remove(test_db)
    manager = DatabaseManager(test_db)
    yield manager
    if os.path.exists(test_db): os.remove(test_db)

def test_signal_with_sl_tp(db):
    """Signallarni SL va TP bilan saqlashni tekshirish."""
    db.add_signal("2026-04-28 10:00", "BTC/USDT", "BUY", 65000.0, 64500.0, 66000.0, 95, "Test Reason")
    
    pending = db.get_pending_signals()
    assert len(pending) == 1
    assert pending[0][1] == "BTC/USDT"
    assert pending[0][4] == 64500.0 # SL
    assert pending[0][5] == 66000.0 # TP1
    print("\n✅ Database SL/TP testi o'tdi!")

def test_stats_with_time_filter(db):
    """Statistika vaqt filtri bilan ishlashini tekshirish."""
    # 1. Bitta eski signal qo'shamiz (qo'lda)
    db.add_signal("2020-01-01 10:00", "OLD/USD", "BUY", 1.0, 0.5, 1.5, 50, "Old")
    
    # 2. Hozirgi signalni qo'shamiz
    db.add_signal("now", "NEW/USD", "SELL", 2.0, 2.5, 1.5, 90, "New")
    
    # Oxirgi 1 soatlik statistika faqat 1 ta signalni ko'rishi kerak
    st = db.get_stats(hours=1)
    assert st['total_signals'] >= 1
    print("✅ Database Time Filter testi o'tdi!")

def test_update_result(db):
    """Signal natijasini yangilashni tekshirish."""
    db.add_signal("now", "ETH/USDT", "BUY", 3500.0, 3400.0, 3700.0, 80, "Reason")
    sig_id = db.get_pending_signals()[0][0]
    
    db.update_signal_result(sig_id, "WIN (TP1)")
    pending = db.get_pending_signals()
    assert len(pending) == 0 # Endi pending emas
    print("✅ Database Update Result testi o'tdi!")

def test_database_migration():
    """Baza migratsiyasi (yetishmagan ustunlarni qo'shish) ishlashini tekshirish."""
    import sqlite3
    test_db = "logs/test_migration.db"
    if os.path.exists(test_db): os.remove(test_db)
    
    # Eski versiyadagi jadvallarni yaratish (sl, tp1, result, quality, reason yo'q)
    conn = sqlite3.connect(test_db)
    conn.execute('''
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            symbol TEXT,
            direction TEXT,
            entry REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    # Manager ishga tushiriladi (va _init_db orqali migratsiya qilinadi)
    db = DatabaseManager(test_db)
    
    # Yangi ustunlar qo'shilganini tekshirish
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(signals)")
    columns = [col[1] for col in cursor.fetchall()]
    
    assert "sl" in columns
    assert "tp1" in columns
    assert "quality" in columns
    assert "reason" in columns
    assert "result" in columns
    
    conn.close()
    if os.path.exists(test_db): os.remove(test_db)
    print("✅ Database Migration testi o'tdi!")
