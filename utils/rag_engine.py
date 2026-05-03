import os
import json
import numpy as np
import logging
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
import google.generativeai as genai

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, api_keys, k_base_dir="bilim_bazasi", index_file="vector_db/index.json"):
        self.k_base_dir = k_base_dir
        self.index_file = index_file
        self.api_keys = api_keys
        
        # Load API key configuration
        if isinstance(api_keys, str):
            keys = [k.strip() for k in api_keys.split(',')]
        else:
            keys = api_keys
        
        if keys:
            genai.configure(api_key=keys[0], transport='rest')
            
        os.makedirs("vector_db", exist_ok=True)
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

    def chunk_text(self, text, chunk_size=1000, overlap=200):
        """Uzun matnni ma'noli bo'laklarga ajratish"""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                # Nuqta or Probelgacha qidirish, so'zni bo'lmaslik uchun
                last_space = text.rfind(' ', start, end)
                if last_space != -1:
                    end = last_space
            chunk = text[start:end].strip()
            if len(chunk) > 50: # Skip very small chunks
                chunks.append(chunk)
            start = end - overlap
            if start >= len(text) - chunk_size // 2:
                break
        return chunks

    def extract_and_chunk_per_file(self):
        """Papkadagi maxsus fayllarni o'qib, fayl nomini qo'shib chunklarga ajratadi"""
        all_chunks = []
        if not os.path.exists(self.k_base_dir):
            return []
            
        for file in os.listdir(self.k_base_dir):
            path = os.path.join(self.k_base_dir, file)
            text = ""
            if file.endswith('.txt'):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                        logger.info(f"Read format TXT: {file}")
                except: pass
            elif file.endswith('.pdf'):
                if PyPDF2 is None:
                    logger.warning(f"Skipping PDF {file} because PyPDF2 is not installed.")
                    continue
                try:
                    with open(path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted: text += extracted + "\n"
                        logger.info(f"Read format PDF: {file}")
                except Exception as e:
                    logger.error(f"Failed to read PDF {file}: {e}")
            
            if len(text) > 10:
                raw_chunks = self.chunk_text(text)
                for chunk in raw_chunks:
                    # Har bir qismga fayl nomini muhrlaymiz
                    all_chunks.append(f"[Kitob/Manba: {file}]\n{chunk}")
                    
        return all_chunks

    async def build_index(self):
        """Bilim bazasidan yangi index noldan yig'ish (Embeddings Generation)"""
        logger.info("Reading PDF/TXT files and building chunks per file...")
        chunks = self.extract_and_chunk_per_file()
        if not chunks:
            return 0
        
        self.documents = []
        self.embeddings = []
        
        # Batching parametrlar - API limitini yemasligi uchun
        import asyncio
        print(f"Toplam qismlar (chunks) soni: {len(chunks)}. Vektorlashtirish boshlandi...")
        for i, chunk in enumerate(chunks):
            try:
                response = genai.embed_content(
                    model="models/gemini-embedding-001",   # Google tasdiqlagan ishchi model
                    content=chunk,
                    task_type="retrieval_document"
                )
                self.embeddings.append(np.array(response['embedding']))
                self.documents.append(chunk)
                
                await asyncio.sleep(0.3)
                if i % 10 == 0:
                    print(f"[{i+1}/{len(chunks)}] chunk vektorizatsiya qilindi...")
            except Exception as e:
                logger.error(f"Embedding error on chunk {i}: {e}")
                print(f"Error on chunk {i}: {e}")
                
        self.save_index()
        print(f"✅ Baza tayyor: Muvaffaqiyatli saqlangan qismlar soni: {len(self.documents)}")
        return len(self.documents)

    def search(self, query, top_k=3):
        """So'rov bilan bazadagi matematika(Cosine Similarity) asosida topish"""
        if not self.embeddings:
            return "Kechirasiz, bilim bazasi indexlanmagan. Iltimos botni yangilang."
            
        try:
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=query,
                task_type="retrieval_query"
            )
            query_emb = np.array(res['embedding'])
            
            # Matritsaviy hisoblash (Juda ham tez)
            query_norm = np.linalg.norm(query_emb)
            similarities = []
            
            for i, emb in enumerate(self.embeddings):
                doc_norm = np.linalg.norm(emb)
                sim = np.dot(query_emb, emb) / (query_norm * doc_norm)
                similarities.append((sim, self.documents[i]))
            
            # Reytingni teshib, TOP kochtini tanlab olamiz
            similarities.sort(key=lambda x: x[0], reverse=True)
            top_docs = [doc for sim, doc in similarities[:top_k]]
            
            # Matnni qovushtirib uzatamiz
            return "\n...\n".join(top_docs)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return ""
