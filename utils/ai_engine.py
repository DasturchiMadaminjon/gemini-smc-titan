import logging
import asyncio
import os
import sys
import base64
from google import genai
from google.genai import types
from datetime import datetime, timezone
from utils.price_fetcher import get_current_price

# Claude kutubxonasini ixtiyoriy import (yo'q bo'lsa ham bot ishlaydi)
try:
    import anthropic as _anthropic
    _CLAUDE_AVAILABLE = True
except ImportError:
    _CLAUDE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIEngine:
    def __init__(self, api_keys=None, model_name="models/gemini-2.5-flash"):
        env_keys = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
        self.api_keys = []
        if api_keys:
            if isinstance(api_keys, list):
                self.api_keys = api_keys
            else:
                self.api_keys = [k.strip() for k in str(api_keys).split(",") if k.strip()]
        elif env_keys:
            self.api_keys = [
                k.strip() for k in env_keys.split(",") if len(k.strip()) > 5
            ]

        self.current_key_index = 0
        self.model_name = model_name
        self.client = None
        self.setup_client()

        # ── Claude integratsiyasi (ixtiyoriy) ──────────────────────────────
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", "").strip()
        self.claude_client = None
        if _CLAUDE_AVAILABLE and self.claude_api_key:
            try:
                self.claude_client = _anthropic.AsyncAnthropic(api_key=self.claude_api_key)
                logger.info("[AI] Claude 3.5 Sonnet mijozi muvaffaqiyatli sozlandi.")
            except Exception as e:
                logger.warning(f"[AI] Claude mijozi sozlanmadi: {e}")
                self.claude_client = None

        # RAG moduli bot.py tomonidan ulanadi
        self.rag = None

        self.setup_personas()

    def setup_client(self):
        """Yangi SDK Client sozlash"""
        if self.api_keys:
            self.client = genai.Client(api_key=self.api_keys[self.current_key_index])
        else:
            self.client = None

    def setup_personas(self):
        self.personas = {
            "technical": "Siz 'SMC TITAN' ekspertisiz. Sizda Vision bor. Grafik va OHLC raqamlarini HAQIQATDAN ko'rib turibsiz. Bahona qilmasdan, aniq raqamlar bilan tahlil bering. MUHIM: Tahlilingizdagi barcha narxlarni (Entry, SL, TP) maksimal 4-5 ta raqamgacha yaxlitlab yozing (Masalan: 1.34567). Javobni oxirigacha tugating.",
            "scalping": "Siz 'SCALP MASTER'siz. Sizda Vision bor. Grafik va narxlarni HAQIQATDAN ko'rib turibsiz. M5/M15 uchun aniq kirish, SL va TP raqamlarini bering. MUHIM: Barcha narxlarni 4-5 ta raqamgacha yaxlitlab yozing. Javobni oxirigacha tugating.",
            "fundamental": (
                "Siz 'MACRO ANALYST' ekspertisiz. Siz FAQAT quyidagi ANIQ FORMAT bo'yicha javob berasiz:\n\n"
                "📌 INSTRUMENT: [nom]\n"
                "💲 JORIY NARX: [raqam] USD\n"
                "📊 MAKRO BIAS: [BULLISH / BEARISH / NEYTRAL] — sababi 1 jumlada\n"
                "🔑 MUHIM DARAJALAR: [Support va Resistance darajalari]\n"
                "📰 ASOSIY DRAYVERLAR: [DXY, FED, energiya, yangiliklar — max 3 ta]\n"
                "🎯 XULOSA: [Trader uchun amaliy maslahat — 2-3 jumla]\n\n"
                "QAT'IYAN TAQIQLANGAN: Umumiy makroekonomik ma'ruza yozish, "
                "'bilmayman' deyish, 2026-yil haqida generic gapirish. "
                "Faqat BERILGAN INSTRUMENT haqida, ANIQ RAQAMLAR bilan javob ber."
            ),
            "chat": "Siz 'SMC MENTOR' yordamchisiz. Savollarga taqdim etilgan bilim bazasi va Google Search qidiruv natijalari asosida aniq javob bering. Bahona qilmang.",
            "evaluator": (
                "Siz 'TITAN SMC MASTER' - botning ASOSIY QAROR CHIQARUVCHI miyasisiz. "
                "Sizga berilayotgan raqamlar (Signal Data) - bu sening o'z indikatoringdan kelgan ANIQ FAKTLAR. "
                "Sizda 'ko'rish' (Vision) bor va grafikni ko'rib turibsiz deb hisoblang. "
                "'Grafikni ko'rmayapman' yoki 'bilmayman' deyish QAT'IYAN TAQIQLANADI. "
                "SMC tamoyillari (BOS, FVG, Liquidity, RR) bo'yicha tahlil bering. "
                "Agar signal sifati (Quality) past bo'lsa yoki RR (Risk/Reward) yomon bo'lsa - rad eting. "
                "Agar hamma narsa to'g'ri bo'lsa - TASDIQLANG."
            ),
            "analytics": "Siz 'Hedge Fund Menejeri'siz. Savdo statistikasini tahlil qiling.",
            "mentor_lessons": "SMC darslarini o'rgatuvchi professional Mentor. Bilim bazasidan foydalaning.",
            "mentor_qa": "SMC Gibrid Mentor. Rasm tahlili va bilim bazasi orqali javob bering. Sizda Vision bor.",
        }

    def _rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.setup_client()
            logger.info(f"API key rotated → index {self.current_key_index}")
            return True
        return False

    async def _get_gemini_analysis(
        self, prompt: str, context_type: str = "technical", image_bytes: bytes = None,
        full_instruction: str = "", contents: list = None
    ) -> str:
        """Gemini orqali tahlil. Bu mavjud Gemini logikasi (o'zgartirilmagan)."""
        if contents is None:
            contents = [prompt]
        # Barcha API kalitlarni aylanish
        for attempt in range(len(self.api_keys)):
            try:
                tools = []
                if context_type in ['chat', 'fundamental', 'mentor_lessons', 'mentor_qa', 'mentor_live_examples']:
                    tools.append(types.Tool(google_search=types.GoogleSearch()))
                config = types.GenerateContentConfig(
                    system_instruction=full_instruction + " MUHIM: Tahlilni to'liq yakunlang va eng oxirida [TAMOM] so'zini yozing.",
                    temperature=0.3,
                    max_output_tokens=8192,
                    tools=tools if tools else None,
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    ]
                )
                accumulated_text = ""
                max_inner_retries = 3
                for inner_attempt in range(max_inner_retries):
                    current_contents = contents.copy()
                    if accumulated_text:
                        current_contents.append(f"Oldingi qism:\n{accumulated_text}\n\nDavom eting:")
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=current_contents,
                        config=config
                    )
                    if not response.text:
                        break
                    accumulated_text += response.text
                    candidate = response.candidates[0] if getattr(response, 'candidates', None) else None
                    finish_reason = str(getattr(candidate, 'finish_reason', '')).upper()
                    if finish_reason and "MAX_OUTPUT_TOKENS" not in finish_reason:
                        break
                    import re as _re
                    acc_upper = accumulated_text.strip().upper()
                    if "[TAMOM]" in acc_upper or _re.search(r'\bTAMOM\b\s*[.!]*$', acc_upper):
                        break
                    await asyncio.sleep(0.5)
                import re as _re
                return _re.sub(r'(?i)\s*\[?TAMOM\]?[.!]*\s*$', '', accumulated_text).strip()
            except Exception as e:
                err = str(e).upper()
                if "403" in err or "PERMISSION_DENIED" in err or "LEAKED" in err:
                    if self._rotate_key():
                        continue
                    return f"❌ Barcha AI kalitlar bloklangan: {err[:50]}"
                if "429" in err or "RESOURCE EXHAUSTED" in err or "LIMIT" in err:
                    if self._rotate_key():
                        continue
                    return f"❌ Barcha AI kalitlar limitga yetdi."
                if "GOOGLE_SEARCH" in err or "400" in err or "INVALID_ARGUMENT" in err:
                    try:
                        config_no_search = types.GenerateContentConfig(
                            system_instruction=full_instruction, temperature=0.3,
                            max_output_tokens=8192,
                            safety_settings=[
                                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                            ]
                        )
                        response = await asyncio.to_thread(
                            self.client.models.generate_content,
                            model=self.model_name, contents=contents, config=config_no_search
                        )
                        return response.text
                    except Exception as e2:
                        logger.error(f"Gemini fallback xatosi: {str(e2)[:50]}")
                return f"❌ AI xatoligi: {str(e)[:100]}"
        return "❌ Barcha API kalitlar band yoki yaroqsiz."

    async def _get_claude_analysis(
        self, prompt: str, context_type: str = "technical",
        image_bytes: bytes = None, full_instruction: str = ""
    ) -> str:
        """Claude 3.5 Sonnet orqali tahlil (ixtiyoriy provayder)."""
        if not self.claude_client:
            raise RuntimeError("Claude mijozi sozlanmagan yoki kalit yo'q.")
        messages = [{"role": "user", "content": []}]
        if image_bytes:
            mime = "image/png" if image_bytes.startswith(b'\x89PNG') else "image/jpeg"
            import base64 as _b64
            messages[0]["content"].append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime,
                           "data": _b64.b64encode(image_bytes).decode()}
            })
        messages[0]["content"].append({"type": "text", "text": prompt})
        response = await self.claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=full_instruction or "Siz professional moliyaviy tahlilchi va SMC treyderini yordamchisisiz.",
            messages=messages
        )
        return response.content[0].text

    async def get_analysis(
        self, prompt: str, context_type: str = "technical",
        image_bytes: bytes = None, provider: str = "GEMINI"
    ) -> str:
        logger.info(f"[ENGINE] context={context_type}, provider={provider}, img={image_bytes is not None}")

        persona = self.personas.get(context_type, self.personas["chat"])
        rag_text = ""
        if self.rag:
            rag_text = self.rag.search(prompt)

        full_instruction = f"{persona}\n\nKontekst: {rag_text}"
        contents = [prompt]
        if image_bytes:
            # Rasm turini aniqlash (PNG: \x89PNG, JPEG: \xff\xd8)
            mime = "image/png" if image_bytes.startswith(b'\x89PNG') else "image/jpeg"
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime)
            )

        # ── PROVIDER TANLASH MANTIQI ────────────────────────────────────────
        use_claude = (
            provider == "CLAUDE"
            and self.claude_api_key
            and self.claude_client is not None
        )

        if use_claude:
            try:
                result = await self._get_claude_analysis(
                    prompt=prompt, context_type=context_type,
                    image_bytes=image_bytes, full_instruction=full_instruction
                )
                logger.info("[ENGINE] Claude javobi muvaffaqiyatli qaytdi.")
                return result
            except Exception as e:
                logger.error(f"[ENGINE] Claude xatosi, Gemini ga o'tilmoqda: {e}")
                # AUTO-FALLBACK: Claude xatoga uchrasa Gemini ishga tushadi

        # Gemini (default yoki fallback)
        if not self.client:
            return "❌ API kalitlari yo'q."
        try:
            return await self._get_gemini_analysis(
                prompt=prompt, context_type=context_type,
                image_bytes=image_bytes,
                full_instruction=full_instruction,
                contents=contents
            )
        except Exception as e:
            logger.error(f"[ENGINE] Gemini ham xatoga uchradi: {e}")
            return f"❌ AI xatoligi: {str(e)[:100]}"



    async def evaluate_trade_signal(self, signal_data: dict, image_bytes: bytes = None) -> tuple[bool, str]:
        """
        Signalni SMC bo'yicha professional tahlil qilish.
        """
        symbol = signal_data.get('symbol', 'Unknown')
        direction = signal_data.get('direction', 'N/A').upper()
        quality = signal_data.get('quality', 0)
        reason = signal_data.get('reason', 'N/A')
        
        prompt = (
            f"🆘 DIQQAT: YANGI SMC SIGNAL ANIQLANDI!\n\n"
            f"📊 INSTRUMENT: {symbol}\n"
            f"🔔 YO'NALISH: {direction}\n"
            f"📥 KIRISH: {signal_data.get('entry', 'N/A')}\n"
            f"🛡 STOP-LOSS: {signal_data.get('sl', 'N/A')}\n"
            f"🎯 MAQSAD (TP1): {signal_data.get('tp1', 'N/A')}\n"
            f"💎 INDIKATOR SIFATI: {quality}%\n"
            f"🧠 INDIKATOR ASOSI: {reason}\n\n"
            f"VAZIFA: Ushbu signalni SMC tamoyillari (Structure, Liquidity, FVG) bo'yicha tahlil qiling. "
            f"Agar {quality} < 60 bo'lsa, qat'iyroq yondashing.\n\n"
            f"🔴 MUHIM QOIDA (VERDICT FIRST): "
            f"Eng birinchi qatorda faqatgina bitta so'z: 'TASDIQLANDI' yoki 'RAD ETILDI' deb yozing. "
            f"Faqat shundan keyingina batafsil tahlilingizni (nima uchun bunday xulosaga kelganingizni) yozishni boshlang!"
        )
        
        # evaluator personasini ishlatamiz
        resp = await self.get_analysis(prompt, context_type="evaluator", image_bytes=image_bytes)
        
        # Tasdiqlash mantiqi (stricter & safer)
        # Xabarning faqat dastlabki 100 ta belgisini tekshiramiz (sababi verdict birinchi qatorda bo'lishi shart)
        first_lines = resp[:100].upper()
        if "TASDIQLANDI" in first_lines or "TASDIQLAYMAN" in first_lines or "APPROVE" in first_lines:
            return True, resp
        return False, resp

