#!/bin/bash

# 🚀 TITAN V27.2 A+ MASTER - STARTUP SCRIPT
# Muallif: Antigravity AI

echo "-----------------------------------------------"
echo "🧬 Titan V27.2 A+ Master Engine ishga tushmoqda..."
echo "-----------------------------------------------"

# 1. Virtual muhitni tekshirish
if [ -d "venv" ]; then
    echo "✅ Virtual muhit topildi. Faollashtirilmoqda..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ .venv topildi. Faollashtirilmoqda..."
    source .venv/bin/activate
else
    echo "⚠️  Virtual muhit topilmadi! Iltimos, 'python3 -m venv venv' orqali yarating."
    exit 1
fi

# 2. Kutubxonalarni tekshirish (ixtiyoriy, tezlik uchun o'chirib qo'yish mumkin)
# pip install -r requirements.txt

# 3. Loglar papkasini tekshirish
mkdir -p logs data

# 4. Botni ishga tushirish (Watchdog orqali)
echo "🐕 Watchdog qo'riqchisi ishga tushmoqda..."
python3 watchdog.py

# Izoh: Agar skript to'xtab qolsa, venv dan chiqish
deactivate
