import sqlite3

for db_path in ['data/titan.db', 'logs/bot_data.db']:
    print(f'\n=== {db_path} ===')
    try:
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f'Jadvallar: {[t[0] for t in tables]}')
        indexes = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'").fetchall()
        if indexes:
            for idx in indexes:
                print(f'  INDEX: {idx[0]} ON {idx[1]}')
                if idx[2]: print(f'    SQL: {idx[2]}')
        else:
            print('  INDEX: YOQ')
        for t in tables:
            cnt = conn.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
            print(f'  {t[0]}: {cnt} ta qator')
        conn.close()
    except Exception as e:
        print(f'  Xato: {e}')
