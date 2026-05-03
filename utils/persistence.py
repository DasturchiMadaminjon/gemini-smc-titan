"""
utils/persistence.py — Kengaytirilgan holat saqlash
Deploy tayyorligi: price_alerts, dedup_cache, onboarding_done ham saqlanadi.
"""
import json, os, logging
from datetime import datetime

logger = logging.getLogger(__name__)

STATE_FILE   = "data/bot_state.json"
EXTRAS_FILE  = "data/extras_state.json"


def load_state():
    """bot_state ni yuklash."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"State o'qishda xato: {e}")
    return None


def save_state(state):
    """bot_state ni saqlash."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"State saqlashda xato: {e}")


def save_extras(price_alerts: dict, dedup_cache: dict, onboarding_done: set):
    """
    Deploy tayyorligi: Restart'dan omon qaladigan qo'shimcha holatlar.
    price_alerts   : {uid: [(sym, price, direction), ...]}
    dedup_cache    : {signal_hash: timestamp_str}
    onboarding_done: {uid1, uid2, ...}
    """
    os.makedirs("data", exist_ok=True)
    data = {
        'price_alerts': {
            str(k): list(v) for k, v in price_alerts.items()
        },
        'dedup_cache': {
            str(k): str(v) for k, v in dedup_cache.items()
        },
        'onboarding_done': list(onboarding_done),
        'saved_at': datetime.utcnow().isoformat()
    }
    try:
        with open(EXTRAS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Extras saqlashda xato: {e}")


def load_extras() -> dict:
    """
    Extras holatni yuklash.
    Returns: {'price_alerts': {...}, 'dedup_cache': {...}, 'onboarding_done': set()}
    """
    result = {'price_alerts': {}, 'dedup_cache': {}, 'onboarding_done': set()}
    if not os.path.exists(EXTRAS_FILE):
        return result
    try:
        with open(EXTRAS_FILE, 'r') as f:
            data = json.load(f)
        # price_alerts: {uid: [(sym, price, dir), ...]}
        for uid, alerts in data.get('price_alerts', {}).items():
            result['price_alerts'][uid] = [tuple(a) for a in alerts]
        # dedup_cache: {hash: ts_str} — str qolsin, datetime kerak emas
        result['dedup_cache'] = data.get('dedup_cache', {})
        # onboarding_done: set
        result['onboarding_done'] = set(data.get('onboarding_done', []))
        logger.info(f"[PERSISTENCE] Extras yuklandi: "
                    f"{len(result['price_alerts'])} alert user, "
                    f"{len(result['dedup_cache'])} dedup entry, "
                    f"{len(result['onboarding_done'])} onboarded user")
    except Exception as e:
        logger.warning(f"Extras o'qishda xato: {e}")
    return result
