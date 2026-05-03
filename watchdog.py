"""
watchdog.py — Sprint 2 #6
Bot crash bo'lganda avtomatik restart + Telegram orqali xabar berish.
Ishlatish: python watchdog.py
"""
import os, time, subprocess, sys, logging, requests, yaml
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | WATCHDOG | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('Watchdog')

HEARTBEAT_FILE = "data/heartbeat.txt"
BOT_SCRIPT     = "bot.py"
CHECK_INTERVAL = 60    # Har 1 daqiqada tekshirish
TIMEOUT        = 900   # 15 daqiqa heartbeat yangilanmasa = freeze
MAX_RESTARTS   = 5     # Soatiga maksimal restart soni

restart_count   = 0
last_reset_hour = datetime.now().hour


def _load_telegram_cfg():
    try:
        with open('config/settings.yaml', 'r') as f:
            cfg = yaml.safe_load(f)
        token   = cfg['telegram']['bot_token']
        chat_id = cfg['telegram']['chat_id'][0]
        return token, str(chat_id)
    except Exception:
        return None, None


def _tg_alert(msg: str):
    """Telegramga favqulodda xabar yuborish (sinxron, watchdog uchun)."""
    token, chat_id = _load_telegram_cfg()
    if not token: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10
        )
    except Exception as e:
        logger.error(f"TG alert xatosi: {e}")


def get_last_heartbeat():
    if not os.path.exists(HEARTBEAT_FILE):
        # Fayl yo'q bo'lsa yaratamiz, aks holda darhol restart beradi
        try:
            os.makedirs('data', exist_ok=True)
            with open(HEARTBEAT_FILE, 'w') as f: f.write(str(time.time()))
        except: pass
        return time.time()
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            return float(f.read().strip())
    except:
        return os.path.getmtime(HEARTBEAT_FILE)


def start_bot():
    logger.info(f"Bot jarayoni boshlanmoqda: {BOT_SCRIPT}")
    return subprocess.Popen([sys.executable, BOT_SCRIPT])


def main():
    global restart_count, last_reset_hour
    logger.info("Gemini Watchdog Engine ishga tushdi.")
    _tg_alert("🐕 <b>Watchdog ishga tushdi.</b>\n\nBot monitoring boshlandi.")

    bot_process = start_bot()

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            # Yangi soat bo'lsa restart hisoblagichni nolga qaytarish
            curr_hour = datetime.now().hour
            if curr_hour != last_reset_hour:
                if restart_count > 0:
                    logger.info(f"[RESET] Soatlik restart hisoblagichi: {restart_count} → 0")
                restart_count = 0
                last_reset_hour = curr_hour

            # 1. Jarayon o'lganini tekshirish
            if bot_process.poll() is not None:
                exit_code = bot_process.returncode
                logger.warning(f"Bot to'xtagan! Exit code: {exit_code}. Restart #{restart_count+1}...")

                if restart_count >= MAX_RESTARTS:
                    msg = (f"🚨 <b>Bot {MAX_RESTARTS} martadan ko'p restart bo'ldi (1 soatda)!</b>\n\n"
                           f"Avtomatik tuzatib bo'lmaydi. Qo'lda tekshirish zarur.\n"
                           f"Watchdog kuzatuvni davom ettiradi...")
                    _tg_alert(msg)
                    logger.error("[WATCHDOG] Soatlik limit. Kutib turamiz...")
                    time.sleep(300)  # 5 daqiqa kutib, davom etadi (o'lmaydi!)
                    restart_count = 0  # Yana urinib ko'ramiz
                    continue

                restart_count += 1
                _tg_alert(
                    f"⚠️ <b>Bot to'xtab qoldi!</b>\n\n"
                    f"Exit code: {exit_code}\n"
                    f"Restart #{restart_count} amalga oshirilmoqda...\n"
                    f"Vaqt: {datetime.now().strftime('%H:%M:%S')}"
                )
                bot_process = start_bot()
                continue

            # 2. Heartbeat yangilanishini tekshirish (Freeze detection)
            last_update = get_last_heartbeat()
            idle_time = time.time() - last_update

            if idle_time > TIMEOUT:
                logger.error(f"Bot 'muzlab' qoldi (Idle: {int(idle_time)}s). RESTART...")
                _tg_alert(
                    f"❄️ <b>Bot muzlab qoldi!</b>\n\n"
                    f"Idle: {int(idle_time // 60)} daqiqa.\n"
                    f"Majburiy restart #{restart_count+1}..."
                )
                restart_count += 1
                bot_process.terminate()
                time.sleep(5)
                if bot_process.poll() is None:
                    bot_process.kill()
                bot_process = start_bot()
            else:
                logger.info(f"✅ Bot sog'lom. Idle: {int(idle_time)}s | Restartlar: {restart_count}")

        except KeyboardInterrupt:
            logger.info("Watchdog to'xtatildi (Ctrl+C).")
            _tg_alert("🛑 <b>Watchdog to'xtatildi</b> (qo'lda). Bot kuzatilmayapti!")
            bot_process.terminate()
            break
        except Exception as e:
            logger.error(f"Watchdog ichki xatosi: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
