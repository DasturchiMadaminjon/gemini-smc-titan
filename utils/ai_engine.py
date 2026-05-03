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
        # API kalitlarini tayyorlash (Agar berilmasa, .env dan oladi)
        if not api_keys:
            env_keys = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
            if env_keys:
                api_keys = [k.strip() for k in env_keys.split(',') if len(k.strip()) > 20]
        
        if isinstance(api_keys, str):
            self.api_keys = [k.strip() for k in api_keys.split(',') if len(k.strip()) > 20]
        else:
            self.api_keys = [k.strip() for k in (api_keys or []) if k and len(k) > 20]
        
        self.current_key_index = 0
        self.model_name = model_name
        self.setup_client()

        # RAG Engine ni yuklash
        try:
            from utils.rag_engine import RAGEngine
            self.rag = RAGEngine(self.api_keys)
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
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
            "fundamental": "Siz 'MACRO ANALYST'siz. 2026-yil voqealari asosida fundamental tahlil qiling.",
            "chat": "Siz 'SMC MENTOR' yordamchisiz. O'zbek tilida, professional javob bering.",
            "analytics": "Siz 'Hedge Fund Menejeri'siz. Savdo statistikasini tahlil qiling.",
            "mentor_lessons": "SMC darslarini o'rgatuvchi professional Mentor. Bilim bazasidan foydalaning.",
            "mentor_qa": "SMC Gibrid Mentor. Savollarga bilim bazasi va rasm tahlili orqali javob bering."
        }

    def _rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.setup_client()
            logger.info(f"API key rotated → index {self.current_key_index}")
            return True
        return False

    async def get_analysis(self, prompt: str, context_type: str = "technical", image_bytes: bytes = None) -> str:
        if not self.client: return "❌ API kalitlari yo'q."
        
        persona = self.personas.get(context_type, self.personas["chat"])
        rag_text = ""
        if self.rag:
            rag_text = self.rag.search(prompt)
        
        full_instruction = f"{persona}\n\nKontekst: {rag_text}"
        contents = [prompt]
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

        # Barcha API kalitlarni aylanish
        for attempt in range(len(self.api_keys)):
            try:
                # 1. Google Search bilan urinib ko'rish (2026-yil standarti: google_search)
                config = types.GenerateContentConfig(
                    system_instruction=full_instruction,
                    temperature=0.7,
                    tools=[get_current_price, types.Tool(google_search=types.GoogleSearch())]
                )
                chat = self.client.chats.create(model=self.model_name, config=config)
                response = chat.send_message(contents)
                return response.text
            except Exception as e:
                err = str(e)
                # Agar Google Search qo'llab-quvvatlanmasa
                if "google_search" in err or "400" in err:
                    try:
                        logger.warning("Google Search fallback faollashdi...")
                        config_no_search = types.GenerateContentConfig(
                            system_instruction=full_instruction,
                            temperature=0.7,
                            tools=[get_current_price]
                        )
                        chat = self.client.chats.create(model=self.model_name, config=config_no_search)
                        response = chat.send_message(contents)
                        return response.text
                    except Exception as e2:
                        err = str(e2)

                if any(x in err for x in ["429", "Resource exhausted", "limit"]):
                    if self._rotate_key(): continue
                return f"❌ AI xatoligi: {err[:100]}"
        return "❌ Barcha API kalitlar band."

    async def evaluate_trade_signal(self, signal_data: dict) -> tuple[bool, str]:
        prompt = f"Signalni SMC bo'yicha tahlil qil va 'Tasdiqlayman' yoki 'Rad etaman' deb javob ber: {signal_data}"
        resp = await self.get_analysis(prompt, context_type="chat")
        lower = resp.lower()
        if "tasdiq" in lower or "to'g'ri" in lower or "yaxshi" in lower:
            return True, resp
        return False, resp
