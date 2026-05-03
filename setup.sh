#!/bin/bash
# ============================================================
#  GEMINI V20 BOT - Server Setup Skripti
#  Ubuntu/Debian serverda ishga tushirish uchun
# ============================================================

set -e
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_USER=$(whoami)

echo "============================================"
echo "  GEMINI SMC TITAN V20 - Server Setup"
echo "============================================"
echo "Papka: $BOT_DIR"
echo ""

# 1. Python paketlarini o'rnatish
echo "[1/4] Python paketlari o'rnatilmoqda..."
pip3 install -r "$BOT_DIR/requirements.txt" --quiet
echo "    OK"

# 2. Logs papkasini yaratish
echo "[2/4] Log papkasi..."
mkdir -p "$BOT_DIR/logs"
echo "    OK"

# 3. Systemd service yaratish
echo "[3/4] Systemd service yaratilmoqda..."
SERVICE_FILE="/etc/systemd/system/gemini-bot.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=GEMINI SMC Titan V20 Trading Bot
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
ExecStart=/usr/bin/python3 $BOT_DIR/bot.py --config $BOT_DIR/config/settings.yaml
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable gemini-bot
echo "    OK"

# 4. Sozlamalarni tekshirish
echo "[4/4] Sozlamalarni tekshirish..."
if grep -q "YOUR_API_KEY" "$BOT_DIR/config/settings.yaml"; then
    echo ""
    echo "⚠️  DIQQAT: config/settings.yaml da API kalitlarini to'ldiring!"
    echo "   exchange.api_key = Birja API kaliti"
    echo "   exchange.api_secret = Birja API sirri"
    echo "   telegram.bot_token = Telegram bot tokeni (@BotFather)"
    echo "   telegram.chat_id = Telegram chat ID (@userinfobot)"
    echo ""
fi

echo "============================================"
echo "  Setup tugallandi!"
echo ""
echo "  Botni ishga tushirish:"
echo "    sudo systemctl start gemini-bot"
echo ""
echo "  Holat tekshirish:"
echo "    sudo systemctl status gemini-bot"
echo ""
echo "  Log ko'rish:"
echo "    sudo journalctl -u gemini-bot -f"
echo ""
echo "  To'xtatish:"
echo "    sudo systemctl stop gemini-bot"
echo ""
echo "  Dashboard:"
echo "    http://SERVER_IP:8080"
echo "============================================"
