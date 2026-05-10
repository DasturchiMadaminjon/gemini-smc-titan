import asyncio
import os
import yaml
from dotenv import load_dotenv
from utils.telegram import TelegramNotifier
import threading

async def test_delivery():
    print("🚀 Telegram xabar yetkazib berish testi boshlandi...")
    
    # 1. Muhitni yuklash
    load_dotenv()
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    lock = threading.Lock()
    
    # 2. Telegram modulini ishga tushirish
    notifier = TelegramNotifier(config, lock)
    
    # 3. Test xabari yuborish
    test_message = (
        "🔔 <b>TEST SIGNAL (DELIVERY CHECK)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Agar ushbu xabarni ko'rayotgan bo'lsangiz, botingiz "
        "Telegram bilan muvaffaqiyatli bog'langan va signallarni "
        "yuborishga tayyor!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📍 Holat: Aloqa a'lo darajada."
    )
    
    print(f"Target IDs: {os.getenv('TELEGRAM_ADMIN_CHAT_ID')}")
    success = await notifier.send(test_message)
    
    if success:
        print("\n✅ MUVAFFAQIYAT! Xabar Telegramga yuborildi.")
    else:
        print("\n❌ XATOLIK! Xabar yuborilmadi. Loglarni tekshiring.")

if __name__ == "__main__":
    asyncio.run(test_delivery())
