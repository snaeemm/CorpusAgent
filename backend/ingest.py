import os
import glob
import json
import uuid
import re
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from google import genai
import fitz  # PyMuPDF
import docx
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pickle

CORPUS_DIR = "../policy_corpus"
CHROMA_DB_DIR = "../chroma_db"
BM25_INDEX_PATH = "../bm25_index.pkl"

def get_gemini_client():
    # Fallback to standard reading if not set
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required in environment.")
    return genai.Client(api_key=api_key)

def extract_text_from_pdf(filepath: str) -> str:
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text
    except Exception as e:
        print(f"Failed to read PDF {filepath}: {e}")
        return ""

def extract_text_from_docx(filepath: str) -> str:
    try:
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Failed to read DOCX {filepath}: {e}")
        return ""

def extract_text_from_md(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read Markdown {filepath}: {e}")
        return ""

# Basic recursive character chunker
def chunk_text(text: str, chunk_size=500, chunk_overlap=50) -> List[str]:
    chunks = []
    # simple split by double newline first
    paragraphs = re.split(r'\n\n+', text)
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) < chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If a single paragraph is longer than size
            if len(p) > chunk_size:
                # split by sentences or just brute-force
                words = p.split()
                cw = []
                clen = 0
                for w in words:
                    if clen + len(w) > chunk_size:
                        chunks.append(" ".join(cw).strip())
                        cw = [w]
                        clen = len(w) + 1
                    else:
                        cw.append(w)
                        clen += len(w) + 1
                if cw:
                    current_chunk = " ".join(cw) + "\n\n"
            else:
                current_chunk = p + "\n\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def ingest_corpus():
    client = get_gemini_client()
    
    # Check if we should ingest
    metadata_path = os.path.join(CORPUS_DIR, "metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Missing {metadata_path}")
        
    with open(metadata_path, "r", encoding="utf-8") as f:
        corpus_metadata = json.load(f)
        
    docs_meta = corpus_metadata.get("documents", {})

    print(f"Ingesting into ChromaDB at {CHROMA_DB_DIR}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    try:
        # idempotency check
        collection = chroma_client.get_collection("meridian_policies")
        if collection.count() > 0:
            print("Corpus already ingested in Chroma. Deleting and refilling to maintain idempotency...")
            chroma_client.delete_collection("meridian_policies")
    except:
        pass
        
    collection = chroma_client.create_collection(name="meridian_policies")
    
    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    files = glob.glob(os.path.join(CORPUS_DIR, "*.*"))
    for file in files:
        filename = os.path.basename(file)
        if filename in ["metadata.json", "eval_questions.json", "README.md"]:
            continue
            
        doc_id = filename.rsplit(".", 1)[0]
        meta = docs_meta.get(doc_id, {})
        
        if filename.endswith(".md"):
            text = extract_text_from_md(file)
        elif filename.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        elif filename.endswith(".docx") or filename.endswith(".doc"):
            text = extract_text_from_docx(file)
        else:
            continue
            
        if not text:
            print(f"Skipping {doc_id} - no text extracted")
            continue
            
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            
            # Save meta ensuring types are valid for Chroma (strings/ints/floats)
            safe_meta = {
                "doc_id": doc_id,
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "department": meta.get("department", ""),
                "effective_date": meta.get("effective_date", ""),
                "superseded_by": meta.get("superseded_by") or "none",
                "format": meta.get("format", ""),
            }
            all_metadatas.append(safe_meta)
            all_ids.append(f"{doc_id}_{i}")

    print(f"Generated {len(all_chunks)} chunks. Embedding...")

    # We embed using Gemini API or locally. The spec allows us to use Gemini.
    # To reduce API calls, we use chunking in batches.
    # Actually, sentence-transformers local BGE is faster and free. But let's use gemini since the specs say "Gemini via Google AI Studio".
    # Wait, the spec says "Embeddings: any ... If you use Gemini embeddings to stay on one provider, note the rate-limit behavior".
    # Since we are on free tier, 15 RPM might be restrictive for ingesting hundreds of chunks. I will use a local sentence-transformer!
    from sentence_transformers import SentenceTransformer
    local_embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    embeddings = local_embedder.encode(all_chunks, batch_size=32, show_progress_bar=True)
    embeddings_list = [emb.tolist() for emb in embeddings]
    
    # Add to Chroma
    batch_size = 100
    for i in range(0, len(all_ids), batch_size):
        collection.add(
            ids=all_ids[i:i+batch_size],
            embeddings=embeddings_list[i:i+batch_size],
            documents=all_chunks[i:i+batch_size],
            metadatas=all_metadatas[i:i+batch_size]
        )
        
    print(f"Chroma Index built with {collection.count()} items.")

    # Build BM25 index
    print("Building BM25 index...")
    tokenized_corpus = [chunk.lower().split() for chunk in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Save BM25 alongside chunks and meta so we can map index back
    bm25_data = {
        "chunks": all_chunks,
        "metadatas": all_metadatas,
        "ids": all_ids,
        "bm25": bm25
    }
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25_data, f)
        
    print("BM25 index saved.")

if __name__ == "__main__":
    ingest_corpus()
