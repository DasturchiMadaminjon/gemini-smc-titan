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
            "chat": "Siz 'SMC MENTOR' yordamchisiz. Savollarga bilim bazasi asosida aniq javob bering. Bahona qilmang.",
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
                # Qat'iy konfiguratsiya
                config = types.GenerateContentConfig(
                    system_instruction=full_instruction + " MUHIM: Tahlilni to'liq yakunlang va eng oxirida [TAMOM] so'zini yozing.",
                    temperature=0.3, # Yanada barqaror javob uchun
                    max_output_tokens=2048,
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    ]
                )

                # Chat sessiyasidan ko'ra generate_content ishonchliroq (stateless)
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=config
                )
                
                if not response.text:
                    raise Exception("AI bo'sh javob qaytardi")
                return response.text
            except Exception as e:
                err = str(e).upper()
                
                # 1. Eng muhimi: Kalit bloklansa, zudlik bilan rotate qilish
                if "403" in err or "PERMISSION_DENIED" in err or "LEAKED" in err:
                    logger.error(f"⚠️ API Key bloklangan (Index {self.current_key_index}): {err[:100]}")
                    if self._rotate_key():
                        continue
                    else:
                        return f"❌ Barcha AI kalitlar bloklangan: {err[:50]}"
                
                # 2. Limit xatolari bo'lsa ham rotate qilish
                if "429" in err or "RESOURCE EXHAUSTED" in err or "LIMIT" in err:
                    logger.warning(f"⚠️ API Key limitga yetdi (Index {self.current_key_index}): {err[:50]}")
                    if self._rotate_key():
                        continue
                    else:
                        return f"❌ Barcha AI kalitlar limitga yetdi."

                # 3. Google Search bilan bog'liq xatolar uchun fallback
                if "GOOGLE_SEARCH" in err or "400" in err or "INVALID_ARGUMENT" in err:
                    try:
                        logger.warning(f"Google Search fallback (Attempt {attempt+1})")
                        config_no_search = types.GenerateContentConfig(
                            system_instruction=full_instruction, 
                            temperature=0.3,
                            max_output_tokens=2048,
                            safety_settings=[
                                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                            ]
                        )
                        response = await asyncio.to_thread(
                            self.client.models.generate_content,
                            model=self.model_name,
                            contents=contents,
                            config=config_no_search
                        )
                        return response.text
                    except Exception as e2:
                        err = str(e2).upper()
                        logger.error(f"Fallback xatosi: {err[:50]}")
                
                # Boshqa xatoliklar bo'lsa qaytaramiz (agar barcha looplar tugasa)
                return f"❌ AI xatoligi: {str(e)[:100]}"
                
        return "❌ Barcha API kalitlar band yoki yaroqsiz."

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
            f"VAZIFA: Ushbu signalni tahlil qiling. Agar {quality} < 60 bo'lsa, qat'iyroq tahlil qiling. "
            f"SMC tamoyillari (Structure, Liquidity, FVG) bo'yicha baho bering. "
            f"Javob oxirida 'TASDIQLAYMAN' yoki 'RAD ETAMAN' deb yozish shart!"
        )
        
        # evaluator personasini ishlatamiz
        resp = await self.get_analysis(prompt, context_type="evaluator", image_bytes=image_bytes)
        lower = resp.lower()
        
        # Tasdiqlash mantiqi (stricter)
        if "tasdiqlayman" in lower or "tasdiq" in lower or "approve" in lower:
            return True, resp
        return False, resp
