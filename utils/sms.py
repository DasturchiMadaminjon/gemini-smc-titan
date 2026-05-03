import requests
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def send_signal_sms(symbol, side, price, tp, sl):
    """
    Savdo signalini qisqa SMS shaklida yuborish
    """
    api_key = os.getenv("INFOBIP_API_KEY")
    base_url = os.getenv("INFOBIP_BASE_URL")
    sender = os.getenv("INFOBIP_SENDER", "Service")
    
    # SMS yuborish ruxsatini tekshirish (ixtiyoriy)
    if not api_key or not base_url:
        logger.warning("SMS tizimi sozlanmagan (.env da kalitlar yo'q)")
        return False

    url = f"https://{base_url}/sms/2/text/advanced"
    
    headers = {
        'Authorization': f'App {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # Signal matni (SMS qisqa va lo'nda bo'lishi kerak)
    # Masalan: GOLD BUY @2328. SL:2320. TP:2350
    text = f"🚀 {symbol} {side.upper()} @{price}\nSL: {sl}\nTP: {tp}"

    payload = {
        "messages": [
            {
                "from": sender,
                "destinations": [{"to": "+998915054701"}], # Sizning tasdiqlangan raqamingiz
                "text": text
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ SMS signal yuborildi: {symbol}")
            return True
        else:
            logger.error(f"❌ SMS yuborishda xato: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ SMS ulanish xatosi: {e}")
        return False
