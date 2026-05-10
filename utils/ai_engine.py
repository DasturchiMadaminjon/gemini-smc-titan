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
            "technical": "Siz 'SMC TITAN' ekspertisiz. Trend, BOS/CHoCH, Demand/Supply zonalar va FVG asosida tahlil bering.",
            "scalping": "Siz 'SCALP MASTER'siz. M5/M15 taymfreymlar uchun tezkor kirish rejasini bering.",
            "fundamental": "Siz 'MACRO ANALYST'siz. 2026-yil voqealari asosida fundamental tahlil qiling. Sizga internetdan real vaqt yangiliklari taqdim etiladi.",
            "chat": "Siz 'SMC MENTOR' yordamchisiz. O'zbek tilida, professional javob bering. Sizda mahalliy bilim bazasi va INTERNET qidiruv imkoniyati bor. Siz rasmlarni o'qib, tahlil qila olasiz. QAT'IY QOIDA: Hech qachon [hozirgi kurs] yoki [sana] kabi qavs ichidagi 'placeholder' ishlatmang. Faqat aniq raqamlarni ayting. Agar internetdan ma'lumot kelgan bo'lsa, o'shani ishlating.",
            "analytics": "Siz 'Hedge Fund Menejeri'siz. Savdo statistikasini tahlil qiling.",
            "mentor_lessons": "SMC darslarini o'rgatuvchi professional Mentor. Bilim bazasi va internet ma'lumotlaridan foydalaning. Placeholder ishlatmang.",
            "mentor_qa": "SMC Gibrid Mentor. Savollarga bilim bazasi, rasm tahlili va internet qidiruvi orqali javob bering. Siz rasmlarni o'qib, tahlil qila olasiz. Faqat aniq ma'lumotlarni bering.",
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
        if not self.client:
            return "❌ API kalitlari yo'q."

        persona = self.personas.get(context_type, self.personas["chat"])
        rag_text = ""
        if self.rag:
            rag_text = self.rag.search(prompt)

        full_instruction = f"{persona}\n\nKontekst: {rag_text}"
        contents = [prompt]
        if image_bytes:
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
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
