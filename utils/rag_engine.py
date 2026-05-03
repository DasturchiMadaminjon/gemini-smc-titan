import os
import json
import numpy as np
import logging
from google import genai
from google.genai import types
import asyncio

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, api_keys=None, k_base_dir="bilim_bazasi", index_file="vector_db/index.json"):
        self.k_base_dir = k_base_dir
        self.index_file = index_file
        
        # API keylarni yuklash (Agar berilmasa, .env dan qidiradi)
        if not api_keys:
            env_keys = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
            if env_keys:
                api_keys = [k.strip() for k in env_keys.split(',') if len(k.strip()) > 20]

        if isinstance(api_keys, str):
            self.keys = [k.strip() for k in api_keys.split(',') if len(k.strip()) > 20]
        else:
            self.keys = [k for k in (api_keys or []) if len(k) > 20]
        
        if not self.keys:
            logger.error("RAG uchun API kalit topilmadi! .env faylini tekshiring.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.keys[0])
        
        os.makedirs("vector_db", exist_ok=True)
        os.makedirs(self.k_base_dir, exist_ok=True)
        
        self.documents = []
        self.embeddings = []
        self.load_index()

    def load_index(self):
        """Lokal fayldan vektorlarni va matnlarni yuklash"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.embeddings = [np.array(e) for e in data.get("embeddings", [])]
                logger.info(f"Loaded {len(self.documents)} chunks from vector memory.")
            except Exception as e:
                logger.error(f"Failed to load RAG index: {e}")
        else:
            logger.info("Vector index not found. Building is required.")

    def save_index(self):
        """Vektorlarni diskka saqlash"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "documents": self.documents,
                    "embeddings": [e.tolist() for e in self.embeddings]
                }, f)
            logger.info(f"Saved {len(self.documents)} chunks to vector memory.")
        except Exception as e:
            logger.error(f"Failed to save RAG index: {e}")

    def chunk_text(self, text, chunk_size=1200, overlap=300):
        """Uzun matnni ma'noli bo'laklarga ajratish (100% qamrov uchun overlap oshirildi)"""
        if not text: return []
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunk = text[start:].strip()
                if len(chunk) > 20: chunks.append(chunk)
                break
                
            last_space = text.rfind(' ', start, end)
            if last_space != -1 and last_space > start:
                end = last_space
            
            chunk = text[start:end].strip()
            if len(chunk) > 20: chunks.append(chunk)
            start = end - overlap
                
        return chunks

    def extract_text_advanced(self, file_path):
        """Fayldan matnni 100% aniqlikda chiqarish (PDF, Word, TXT)"""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.pdf':
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text: text += page_text + "\n"
            elif ext == '.docx':
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"Extraction error ({file_path}): {e}")
        return text

    async def build_index(self, force=False):
        """Barcha kitoblarni o'qib, yangi index yig'ish"""
        if not force and self.documents:
            logger.info("Index already exists. Skipping build.")
            return len(self.documents)

        logger.info("Building 100% Knowledge Base Index...")
        all_chunks = []
        
        for file in os.listdir(self.k_base_dir):
            path = os.path.join(self.k_base_dir, file)
            text = self.extract_text_advanced(path)
            if len(text) > 50:
                raw_chunks = self.chunk_text(text)
                for chunk in raw_chunks:
                    all_chunks.append(f"[Manba: {file}]\n{chunk}")
                logger.info(f"Processed {file}: {len(raw_chunks)} chunks")

        if not all_chunks: return 0

        self.documents = []
        self.embeddings = []
        
        # Batch embedding using new SDK
        for i, chunk in enumerate(all_chunks):
            try:
                # google-genai SDK embedding
                res = self.client.models.embed_content(
                    model="models/gemini-embedding-001", 
                    contents=chunk,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                )
                self.embeddings.append(np.array(res.embeddings[0].values))
                self.documents.append(chunk)
                
                if i % 10 == 0: logger.info(f"Indexing progress: {i}/{len(all_chunks)}")
                await asyncio.sleep(0.5) # Rate limit protection
            except Exception as e:
                logger.error(f"Embedding error: {e}")

        self.save_index()
        return len(self.documents)

    def search(self, query, top_k=8):
        """Vektorli qidiruv va fayllar ro'yxati nazorati (Fix 404)"""
        # 1. Fayllar ro'yxati haqida so'ralganini aniqlash
        is_list_query = any(x in query.lower() for x in ["qanday kitob", "nechta fayl", "fayllar ro'yxati", "nimalar bor", "qanaqa kitob"])
        stats = self.get_kb_stats()
        available_files = "\n".join([f"- {f['name']} ({f['size_kb']} KB)" for f in stats['files']])
        context = f"Tizimdagi haqiqiy fayllar ro'yxati:\n{available_files}\n\n" if is_list_query else ""

        # 2. Agar index bo'lmasa yoki qidiruv xatosi bo'lsa, faqat ro'yxatni qaytarish
        if not self.embeddings: 
            return context

        try:
            # Muhim: Model nomi aniq gemini-embedding-001 bo'lishi shart
            res = self.client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=query,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            )
            query_emb = np.array(res.embeddings[0].values)
            
            similarities = []
            for i, emb in enumerate(self.embeddings):
                # Cosine similarity
                sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-9)
                similarities.append((sim, self.documents[i]))
            
            similarities.sort(key=lambda x: x[0], reverse=True)
            search_results = "\n...\n".join([doc for sim, doc in similarities[:top_k]])
            return context + search_results
        except Exception as e:
            logger.error(f"Search error (RAG): {e}")
            return context # Xato bo'lsa ham kamida fayllar ro'yxatini qaytarsin

    def get_kb_stats(self):
        """AWS va lokal uchun statistika"""
        stats = {"total_files": 0, "files": [], "total_chunks": len(self.documents), "total_size_kb": 0}
        if not os.path.exists(self.k_base_dir): return stats
        for file in os.listdir(self.k_base_dir):
            path = os.path.join(self.k_base_dir, file)
            size = os.path.getsize(path) / 1024
            stats["total_files"] += 1
            stats["total_size_kb"] += size
            stats["files"].append({"name": file, "size_kb": round(size, 2)})
        return stats
