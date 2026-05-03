import sys, os
sys.path.insert(0, os.path.abspath('.'))
from utils.database import DatabaseManager
from utils.analytics import generate_trade_report

def run_test():
    db = DatabaseManager()
    
    # Keling, oldingi barcha ma'lumotlarni tozalab, sof holatda test qilamiz
    db.clear_all_stats()
    
    # 30 ta yutuq, 41 ta yutqiziq kiritamiz (jami 71 ta)
    for i in range(30):
        db.add_history('10:00', 'EUR/USD', 'BUY', 1.0500, 'WIN (TP1)', 2.0)
        db.add_signal('EUR/USD', 'BUY', 1.0500, 1.0400, 1.0700)
    
    for i in range(41):
        db.add_history('11:00', 'GBP/USD', 'SELL', 1.3000, 'LOSS (SL)', -1.0)
        db.add_signal('GBP/USD', 'SELL', 1.3000, 1.3100, 1.2800)
        
    # Keling test hisobotni ekranga chiqaramiz
    report = generate_trade_report()
    print("===================")
    print("KOD TOMONIDAN YARATILGAN XISOBOT (AI GA YUBORILADIGAN):")
    print(report)
    print("===================")

if __name__ == '__main__':
    run_test()
