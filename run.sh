#!/bin/bash

# 🚀 TITAN V27.2 A+ MASTER - BACKGROUND STARTUP SCRIPT
# Muallif: Antigravity AI

LOG_FILE="bot_log.txt"
PID_FILE="bot.pid"

echo "-----------------------------------------------"
echo "🧬 Titan V27.2 A+ Master Engine ishga tushmoqda..."
echo "-----------------------------------------------"

# 1. Virtual muhitni tekshirish va faollashtirish
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️  Virtual muhit topilmadi!"
    exit 1
fi

# 2. Eskisini to'xtatish (agar bo'lsa)
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if ps -p $old_pid > /dev/null; then
        echo "🛑 Eski jarayon (PID: $old_pid) to'xtatilmoqda..."
        kill $old_pid
        sleep 2
    fi
fi

# 3. Orqa fonda ishga tushirish (NOHUP)
echo "🐕 Watchdog orqa fonda ishga tushmoqda..."
nohup python3 watchdog.py > "$LOG_FILE" 2>&1 &

# 4. Yangi PID ni saqlash
new_pid=$!
echo $new_pid > "$PID_FILE"

echo "✅ Bot muvaffaqiyatli ishga tushdi! (PID: $new_pid)"
echo "📊 Kuzatish uchun: tail -f $LOG_FILE"
echo "-----------------------------------------------"
