import logging
import asyncio
import os
import sys
import base64
from google import genai
from google.genai import types
from datetime import datetime, timezone
from utils.price_fetcher import get_current_price

logger = logging.getLogger(__name__)


class AIEngine:
    def __init__(self, api_keys=None, model_name="models/gemini-2.5-flash"):
        env_keys = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
        self.api_keys = []
        if api_keys:
            self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        elif env_keys:
            self.api_keys = [
                k.strip() for k in env_keys.split(",") if len(k.strip()) > 20
            ]

        self.current_key_index = 0
        self.model_name = model_name
        self.client = None
        self.setup_client()

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
            "technical": "Siz 'SMC TITAN' ekspertisiz. Sizda Vision (ko'rish) bor. Grafik va OHLC raqamlarini HAQIQATDAN ko'rib turibsiz. Bahona qilmasdan, aniq raqamlar bilan tahlil bering.",
            "scalping": "Siz 'SCALP MASTER'siz. Sizda Vision bor. Grafik va narxlarni HAQIQATDAN ko'rib turibsiz. 'Ko'rolmayman' deyish QAT'IYAN TAQIQLANADI. M5/M15 uchun aniq kirish, SL va TP raqamlarini bering.",
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
            "chat": "Siz 'SMC MENTOR' yordamchisiz. Siz rasmlarni HAQIQATDAN ko'ra olasiz. Savollarga rasm va bilim bazasi asosida aniq javob bering. Bahona qilmang.",
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

    async def get_analysis(
        self, prompt: str, context_type: str = "technical", image_bytes: bytes = None
    ) -> str:
        # Debug log: AI Engine rasm qabul qildimi?
        logger.info(f"[ENGINE-DEBUG] context={context_type}, img_bytes_received={image_bytes is not None}")
        
        if not self.client:
            return "❌ API kalitlari yo'q."

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

        # Barcha API kalitlarni aylanish
        for attempt in range(len(self.api_keys)):
            try:
                # 1. Google Search bilan urinib ko'rish
                # SDK muvofiqligi uchun eng sodda va xavfsiz konfiguratsiya
                config = types.GenerateContentConfig(
                    system_instruction=full_instruction,
                    temperature=0.7,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                )
                import asyncio

                chat = self.client.chats.create(model=self.model_name, config=config)
                response = await asyncio.to_thread(chat.send_message, contents)
                return response.text
            except Exception as e:
                err = str(e)
                # Agar Google Search yoki ruxsat bilan bog'liq xato bo'lsa (masalan, API key ruxsat bermasa)
                if "google_search" in err or "400" in err or "INVALID_ARGUMENT" in err:
                    try:
                        logger.warning(
                            f"Google Search fallback (Attempt {attempt+1}): {err[:50]}"
                        )
                        config_no_search = types.GenerateContentConfig(
                            system_instruction=full_instruction, temperature=0.7
                        )
                        import asyncio

                        chat = self.client.chats.create(
                            model=self.model_name, config=config_no_search
                        )
                        response = await asyncio.to_thread(chat.send_message, contents)
                        return response.text
                    except Exception as e2:
                        err = str(e2)

                if any(x in err for x in ["429", "Resource exhausted", "limit"]):
                    if self._rotate_key():
                        continue
                return f"❌ AI xatoligi: {err[:100]}"
        return "❌ Barcha API kalitlar band."

    async def evaluate_trade_signal(self, signal_data: dict) -> tuple[bool, str]:
        prompt = f"Signalni SMC bo'yicha tahlil qil va 'Tasdiqlayman' yoki 'Rad etaman' deb javob ber: {signal_data}"
        resp = await self.get_analysis(prompt, context_type="chat")
        lower = resp.lower()
        if "tasdiq" in lower or "to'g'ri" in lower or "yaxshi" in lower:
            return True, resp
        return False, resp
