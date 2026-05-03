import json
from utils.database import DatabaseManager

def generate_trade_report(bot_state=None):
    """
    Tarixiy signallarni bazadan o'qib, AI tahlili uchun matnli hisobot yaratadi.
    """
    db = DatabaseManager()
    st = db.get_stats(limit=50)
    
    if st['total_signals'] == 0:
        return "Bot hozircha hech qanday signal ishlamagan. Barcha ma'lumotlar nolda turibdi."

    report_text = f"XISOBOT TAQDIM ETILDI:\n- Jami Yuborilgan Signallar: {st['total_signals']}\n"
    report_text += f"- Yopilgan bitimlar (Oxirgi): {st['total']}\n"
    report_text += f"- Foydali (Win/TP): {st['tp']}\n- Zararli (Loss/SL): {st['sl']}\n"
    report_text += f"- Win-Rate: {st['winrate']}%\n- Jami Foyda (R): {st['profit']}\n\n"

    report_text += "\nUshbu statistikani o'qib fond menejeri sifatida qisqa xulosa bering va kelasi xaftaga strategik tavsiya tugiting."
    return report_text
