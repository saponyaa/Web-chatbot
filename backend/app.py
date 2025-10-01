from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import logging

from .document_parser import extract_text_from_file
from .embeddings import get_embedding
from .qdrant_utils import insert_vectors, search_vectors

# -----------------------------------------------------------
# Initialize FastAPI
# -----------------------------------------------------------
app = FastAPI(title="Web Chatbot Backend")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# Endpoint 1: Upload file
# -----------------------------------------------------------
@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        chunks = extract_text_from_file(file)

        if not chunks:
            return {"status": "error", "message": "No text could be extracted."}

        for i, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            insert_vectors(vector, {
                "source": file.filename,
                "chunk": i,
                "text": chunk
            })

        return {
            "status": "success",
            "chunks_inserted": len(chunks),
            "message": f"Inserted {len(chunks)} chunks from {file.filename}"
        }

    except Exception as e:
        logger.error(f"Upload file failed: {e}")
        return {"status": "error", "message": str(e)}


# -----------------------------------------------------------
# Endpoint 2: Upload CMS content
# -----------------------------------------------------------
@app.post("/upload-cms/")
async def upload_cms(contents: List[Dict]):
    try:
        if not contents:
            return {"status": "error", "message": "No CMS content provided."}

        for i, chunk in enumerate(contents):
            text = chunk.get("content", "")
            source = chunk.get("title", "cms")
            if not text.strip():
                continue

            vector = get_embedding(text)
            insert_vectors(vector, {
                "source": source,
                "chunk": i,
                "text": text
            })

        return {
            "status": "success",
            "chunks_inserted": len(contents),
            "message": f"Inserted {len(contents)} CMS chunks"
        }

    except Exception as e:
        logger.error(f"Upload CMS failed: {e}")
        return {"status": "error", "message": str(e)}


# -----------------------------------------------------------
# Endpoint 3: Ask question
# -----------------------------------------------------------

import re
import string
from fastapi import Form

# Stopwords for token scoring
STOPWORDS = {
    "the","is","a","an","and","or","for","to","of","in","on","do","you","what",
    "how","are","we","our","your","it","with","by","from","that","this","be","can"
}

# Expanded domain keywords for relevance filtering
DOMAIN_KEYWORDS = {
    "refund","return","policy","shipping","ship","discount","student","support",
    "contact","help","customer","service","email","phone","days","processing",
    "payment","track","tracking"
}

SIMILARITY_THRESHOLD = 0.3
TOP_K_CHUNKS = 5
MAX_ANSWER_SENTENCES = 3  # combine up to 3 top sentences

def _tokenize(text):
    return [w.strip(string.punctuation) for w in text.lower().split() if w.strip(string.punctuation)]

def _is_question_label(s):
    return s.strip().endswith("?") or bool(re.match(r'^\s*(q\d*\s*[:\-\)]|question\s*[:\-\)])', s, re.IGNORECASE))

def _is_answer_label(s):
    return bool(re.match(r'^\s*(a\d*\s*[:\-\)]|answer\s*[:\-\)])', s, re.IGNORECASE))

def _score_sentence(sentence, q_tokens):
    s_lower = sentence.lower()
    s_tokens = set(_tokenize(sentence))
    overlap = sum(1 for t in q_tokens if t not in STOPWORDS and t in s_tokens)

    score = float(overlap)
    if _is_question_label(sentence):
        score -= 100.0
    if _is_answer_label(sentence):
        score += 2.0
    if any(k in s_lower for k in DOMAIN_KEYWORDS):
        score += 2.0
    if re.search(r'\d', sentence):
        score += 1.0
    if re.search(r'\b(yes|no)\b', s_lower):
        score += 1.5
    if len(s_tokens) <= 2:
        score -= 0.5
    return score

def _chunk_is_relevant(chunk_text, question_tokens):
    chunk_tokens = set(_tokenize(chunk_text))
    overlap = sum(1 for t in question_tokens if t not in STOPWORDS and t in chunk_tokens)
    contains_keyword = any(k in chunk_text.lower() for k in DOMAIN_KEYWORDS)
    return overlap > 0 or contains_keyword

@app.post("/ask/")
async def ask_question(question: str = Form(...)):
    try:
        vector = get_embedding(question)
        results = search_vectors(vector, top=TOP_K_CHUNKS)

        if not results:
            return {"answer": "I could not find an answer in the documents.", "sources": []}

        # Filter by minimal similarity
        results = [r for r in results if getattr(r, "score", 0) >= SIMILARITY_THRESHOLD]
        if not results:
            return {"answer": "I could not find an answer in the documents.", "sources": []}

        # Deduplicate chunks and collect sources
        seen = set()
        unique_results = []
        sources = []
        for res in results:
            meta = res.payload
            key = (meta.get("source"), meta.get("chunk"))
            if key not in seen:
                seen.add(key)
                unique_results.append(res)
                sources.append({"source": meta.get("source", "unknown"), "chunk": meta.get("chunk", 0)})

        # Prepare question tokens
        q_tokens = set(_tokenize(question))

        # Collect candidate sentences from relevant chunks
        candidates = []
        for res in unique_results:
            chunk_text = res.payload.get("text", "").strip()
            if not chunk_text or not _chunk_is_relevant(chunk_text, q_tokens):
                continue
            sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+|\n+', chunk_text) if s.strip()]
            for s in sentences:
                candidates.append((s, _score_sentence(s, q_tokens)))

        if not candidates:
            # fallback to first 400 chars of first relevant chunk
            best_answer = unique_results[0].payload.get("text", "")[:400].strip()
            if len(unique_results[0].payload.get("text", "")) > 400:
                best_answer += "..."
            return {"answer": best_answer, "sources": sources}

        # Sort sentences by score and pick top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s for s, score in candidates[:MAX_ANSWER_SENTENCES]]
        best_answer = " ".join(top_sentences)

        # Clean answer prefixes
        best_answer = re.sub(r'^\s*(A\d*[:\-\)]\s*)', '', best_answer, flags=re.IGNORECASE)
        best_answer = re.sub(r'^\s*(Answer[:\-\)]\s*)', '', best_answer, flags=re.IGNORECASE)

        return {"answer": best_answer, "sources": sources}

    except Exception as e:
        return {"answer": f"Error: {str(e)}", "sources": []}
