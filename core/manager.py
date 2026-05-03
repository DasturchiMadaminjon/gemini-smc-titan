import logging
import hashlib
from datetime import datetime, timezone, timedelta
from utils.position_sizer import format_position_line

logger = logging.getLogger(__name__)

class TradeManager:
    """
    Sprint 1 Yangilanishlari:
    ✅ #1 — Signal bilan birga chart rasm yuborish
    ✅ #2 — Duplicate signal deduplication (hash, 30 daqiqa)
    ✅ #4 — Loss streak >= 3 riskni avtomatik kamaytirish
    ✅ #6 — Signal xabariga ✅ TP / ❌ SL inline tugmalari
    """

    def __init__(self, config, db, notifier):
        self.cfg = config
        self.notifier = notifier
        self.db = db
        self.loss_streak = 0
        # Deduplication: {signal_hash: timestamp}
        self._sent_signals: dict = {}
        self.DEDUP_WINDOW_MIN = 30  # bir xil signal 30 daqiqa ichida qayta kelmaydi

    # ─── Deduplication ────────────────────────────────────────────────────────
    def _signal_hash(self, sym: str, direction: str, entry: float) -> str:
        """Signal uchun noyob hash yaratish."""
        raw = f"{sym}:{direction}:{entry:.4f}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _is_duplicate(self, sym: str, direction: str, entry: float) -> bool:
        """Oxirgi DEDUP_WINDOW_MIN daqiqada bir xil signal yuborilganmi?"""
        h = self._signal_hash(sym, direction, entry)
        now = datetime.now(timezone.utc)
        if h in self._sent_signals:
            age = (now - self._sent_signals[h]).total_seconds() / 60
            if age < self.DEDUP_WINDOW_MIN:
                logger.info(f"[DEDUP] {sym} {direction} — {age:.1f} daqiqa oldin yuborilgan, skip.")
                return True
        self._sent_signals[h] = now
        # Eskilarni tozalash (xotira tejash)
        cutoff = now - timedelta(minutes=self.DEDUP_WINDOW_MIN * 2)
        self._sent_signals = {k: v for k, v in self._sent_signals.items() if v > cutoff}
        return False

    # ─── Streak va Risk Himoyasi ───────────────────────────────────────────────
    def _get_effective_risk(self) -> float:
        """
        Sprint 1 #4: Loss streak >= 3 bo'lsa riskni avtomatik kamaytirish.
        streak=0-2 → normal risk
        streak=3-4 → risk/2
        streak>=5  → risk/4 (maksimal himoya)
        """
        base_risk = float(self.cfg.get('trend', {}).get('risk_perc', 2.0))
        if self.loss_streak >= 5:
            effective = base_risk / 4
            logger.warning(f"[STREAK] {self.loss_streak} ta zarar! Risk {effective:.1f}% ga tushirildi.")
            return effective
        elif self.loss_streak >= 3:
            effective = base_risk / 2
            logger.warning(f"[STREAK] {self.loss_streak} ta zarar! Risk {effective:.1f}% ga tushirildi.")
            return effective
        return base_risk

    # ─── Asosiy Signal Yuborish ────────────────────────────────────────────────
    async def process_and_send_signal(self, sym, sig, state, ai_reason=None, chart_buf=None):
        """
        Sprint 1 Yangi Imzo:
        - chart_buf: ixtiyoriy bytes — signal bilan birga chart rasm
        - Deduplication avtomatik tekshiriladi
        - Effective risk streak ga qarab hisoblanadi
        - TP/SL inline tugmalari qo'shiladi
        """
        if not sig:
            return

        # ✅ #2 Deduplication
        if self._is_duplicate(sym, sig.direction, sig.entry):
            return

        balance = state.get('terminal', {}).get('balance', 5000.0)

        # ✅ #4 Streak himoyasi
        risk_pct = self._get_effective_risk()
        base_risk = float(self.cfg.get('trend', {}).get('risk_perc', 2.0))
        streak_warning = ""
        if self.loss_streak >= 3:
            streak_warning = (
                f"\n⚠️ <b>OGOHLANTIRISH:</b> {self.loss_streak} ta ketma-ket zarar!\n"
                f"Risk avtomatik {base_risk}% → <b>{risk_pct:.1f}%</b> ga tushirildi.\n"
            )

        direction_str = "🟢 BUY (LONG)" if sig.direction == 'buy' else "🔴 SELL (SHORT)"

        pos_line = format_position_line(
            balance, risk_pct, sig.entry, sig.sl, sig.tp1, sig.tp2, sym
        )

        from datetime import datetime, timedelta, timezone
        uzt = datetime.now(timezone.utc) + timedelta(hours=5)
        terminal_time = sig.timestamp.strftime('%H:%M') if hasattr(sig.timestamp, 'strftime') else str(sig.timestamp)

        if self.cfg.get('trend', {}).get('fibo_split_enabled', True):
            e2 = sig.entry - (sig.entry - sig.sl) * 0.382
            msg  = f"🚀 <b>YANGI SIGNAL: {sym}</b>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🔔 Signal: <b>{direction_str}</b>\n"
            msg += f"💎 Sifat: <code>{sig.quality:.1f}%</code>\n"
            if streak_warning:
                msg += streak_warning
            msg += f"\n📥 1-Kirish: <code>{sig.entry:.5g}</code>\n"
            msg += f"📥 2-Kirish: <code>{e2:.5g}</code>\n"
            msg += f"🛡 Stop-Loss: <code>{sig.sl:.5g}</code>\n\n"
            msg += f"🎯 Maqsadlar:\n"
            msg += f"   1. TP1: <code>{sig.tp1:.5g}</code>\n"
            msg += f"   2. TP2: <code>{sig.tp2:.5g}</code>\n"
            msg += f"   3. TP3: <code>{sig.tp3:.5g}</code>\n\n"
            msg += f"🧠 <b>Asos:</b> {sig.reason}\n"
            if ai_reason:
                msg += f"\n🤖 <b>AI Xulosasi:</b> {ai_reason}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🕐 <b>UZT:</b> {uzt.strftime('%H:%M')} | 🏛 <b>Terminal:</b> {terminal_time}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += pos_line + "\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"⚡ Titan V27.2 Master"
        else:
            msg = f"🚀 Signal: {sym} @ {sig.entry}\nSL: {sig.sl}\n{pos_line}"

        # ✅ #6: TP/SL inline tugmalari
        import json
        sig_id = self._signal_hash(sym, sig.direction, sig.entry)
        ikb = {'inline_keyboard': [[
            {'text': "✅ TP urdi", 'callback_data': f"sig_tp:{sig_id}:{sym}"},
            {'text': "❌ SL urdi", 'callback_data': f"sig_sl:{sig_id}:{sym}"},
            {'text': "⏭ O'tkazdim", 'callback_data': f"sig_skip:{sig_id}:{sym}"}
        ]]}

        # ✅ #1: Chart rasm bilan birga yuborish
        if chart_buf:
            try:
                await self.notifier.telegram.send_photo(
                    photo=chart_buf, caption=msg, kb=json.dumps(ikb)
                )
            except Exception:
                # Fallback: rasm kelmasa matn yuboramiz
                await self.notifier.telegram.send(msg, kb=json.dumps(ikb))
        else:
            await self.notifier.telegram.send(msg, kb=json.dumps(ikb))

    def handle_loss(self):
        self.loss_streak += 1

    def handle_win(self):
        self.loss_streak = 0
