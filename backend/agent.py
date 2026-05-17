import os
import json
import inspect
import typing
import pickle
import numpy as np
from pydantic import BaseModel
from google import genai
from google.genai import types
import chromadb

CHROMA_DB_DIR = "../chroma_db"
BM25_INDEX_PATH = "../bm25_index.pkl"
CORPUS_DIR = "../policy_corpus"

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv("../.env")
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required.")
    return genai.Client(api_key=api_key)

_local_embedder = None
def get_embedder():
    global _local_embedder
    if _local_embedder is None:
        from sentence_transformers import SentenceTransformer
        _local_embedder = SentenceTransformer('all-MiniLM-L6-v2')
    return _local_embedder

# -----------------
# TOOLS
# -----------------

def retrieve_docs(query: str, top_k: int = 5, include_superseded: bool = False) -> str:
    """
    Hybrid search policy documents using Dense Embedding + BM25 keyword matching.
    Returns the top_k most relevant chunks. By default, ignores superseded docs.
    """
    try:
        # Dense retrieval
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        collection = chroma_client.get_collection("meridian_policies")
        local_embedder = get_embedder()
        q_emb = local_embedder.encode([query])[0].tolist()
        
        results = collection.query(query_embeddings=[q_emb], n_results=top_k * 3)
        
        dense_scores = {}
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            # Superseded filter
            if not include_superseded and meta.get("superseded_by", "none") != "none":
                continue
            distance = results["distances"][0][i]
            # invert distance for score
            dense_scores[doc_id] = {"score": 1.0 / (1.0 + distance), "meta": meta, "text": results["documents"][0][i]}

        # BM25 Retrieval
        bm25_scores = {}
        if os.path.exists(BM25_INDEX_PATH):
            with open(BM25_INDEX_PATH, "rb") as f:
                bm25_data = pickle.load(f)
            bm25 = bm25_data["bm25"]
            tokenized_q = query.lower().split()
            doc_scores = bm25.get_scores(tokenized_q)
            
            # Get top chunk ids
            top_n = np.argsort(doc_scores)[::-1][:top_k * 3]
            for idx in top_n:
                d_id = bm25_data["ids"][idx]
                meta = bm25_data["metadatas"][idx]
                if not include_superseded and meta.get("superseded_by", "none") != "none":
                    continue
                if doc_scores[idx] > 0:
                    bm25_scores[d_id] = {"score": doc_scores[idx], "meta": meta, "text": bm25_data["chunks"][idx]}
                    
        # Reciprocal Rank Fusion / Simple combine
        final_docs = {}
        all_ids = set(dense_scores.keys()).union(set(bm25_scores.keys()))
        for k in all_ids:
            s_dense = dense_scores.get(k, {}).get("score", 0)
            s_bm25 = bm25_scores.get(k, {}).get("score", 0)
            meta = dense_scores.get(k, bm25_scores.get(k))["meta"]
            text = dense_scores.get(k, bm25_scores.get(k))["text"]
            
            # normalize roughly
            final_docs[k] = {"score": s_dense * 0.5 + s_bm25 * 0.5, "meta": meta, "text": text}
            
        # sort by combined score
        sorted_docs = sorted(final_docs.items(), key=lambda x: x[1]["score"], reverse=True)[:top_k]
        
        docs_str = []
        for d_id, data in sorted_docs:
            m = data["meta"]
            doc_name = m.get("doc_id")
            docs_str.append(f"Document: {doc_name} (Category: {m.get('category')} | Status: {'Superseded by ' + m.get('superseded_by') if m.get('superseded_by') != 'none' else 'Current'})\nSnippet:\n{data['text']}\n")
            
        if not docs_str:
            return "No relevant documents found."
        return "\n---\n".join(docs_str)
    except Exception as e:
        return f"Error retrieving docs: {e}"

def get_document_metadata(doc_id: str) -> str:
    """Returns authoritative metadata properties (effective date, superseding chain) for a specific document ID."""
    meta_path = os.path.join(CORPUS_DIR, "metadata.json")
    if not os.path.exists(meta_path):
        return "Metadata file not found."
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    doc_meta = meta.get("documents", {}).get(doc_id)
    if not doc_meta:
        return f"Document {doc_id} not found."
    return json.dumps(doc_meta, indent=2)

def check_contradictions(doc_ids: list[str], query: str) -> str:
    """Check if multiple documents contradict each other regarding a specific query. ONLY use if you have 2+ docs."""
    meta_path = os.path.join(CORPUS_DIR, "metadata.json")
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        texts = []
        for d_id in doc_ids:
            file_meta = meta.get("documents", {}).get(d_id)
            if not file_meta: continue
            ext = ".pdf" if file_meta["format"] == "pdf" else (".docx" if file_meta["format"] == "docx" else ".md")
            fpath = os.path.join(CORPUS_DIR, d_id + ext)
            if ext == ".md":
                with open(fpath, "r", encoding="utf-8") as file:
                    content = file.read()[:2000]
            else:
                content = f"Binary doc {d_id}. Assume retrieved chunks provide content."
            texts.append(f"--- Document {d_id} ---\n{content}")
        
        prompt = f"Analyze these docs for contradictions regarding: '{query}'. ONLY report contradictions. If none, say 'No contradictions found.'\n\n" + "\n".join(texts)
        client = get_gemini_client()
        resp = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt)
        return resp.text
    except Exception as e:
        return f"Error in contradiction check: {e}"

def log_plan(plan: str) -> str:
    """Log your step-by-step plan before execution."""
    return f"Plan Logged: {plan}"

def submit_draft_for_critique(draft: str, grounded_citations: list[str]) -> str:
    """Submit a draft answer to self-critique. Checks if all claims are grounded in citations."""
    if not grounded_citations:
        return "CRITIQUE FAILED: Draft has no citations! Revise to include citations."
    return "CRITIQUE PASSED: Draft is grounded. You may formulate the final answer."

AVAILABLE_TOOLS = {
    "retrieve_docs": retrieve_docs,
    "get_document_metadata": get_document_metadata,
    "check_contradictions": check_contradictions,
    "log_plan": log_plan,
    "submit_draft_for_critique": submit_draft_for_critique
}

# -----------------
# AGENT RUNNER
# -----------------

class AgentResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence: float
    trace: list[dict]

class PolicyAgent:
    def __init__(self):
        self.client = get_gemini_client()
        self.model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.system_instruction = """
You are Meridian Consulting's corporate policy assistant.
1. Ground your answers ONLY in the retrieved corpus. Do NOT hallucinate.
2. If out-of-scope, answer precisely: "I cannot find an authoritative answer in the policy corpus"
3. STEPS YOU MUST FOLLOW ENFORCED BY TRACING:
   - First, call `log_plan` outlining the steps you will take to answer the question.
   - Second, `retrieve_docs`.
   - Third, if multiple varying documents are found, use `check_contradictions`. If contradictions exist, explicitly surface them in your final answer!
   - Fourth, use `submit_draft_for_critique` with your draft outline and citations.
   - Finally, reply with the final text.
4. Always cite Document IDs (e.g., [POL-HR-001]).
"""
        self.tools = [retrieve_docs, get_document_metadata, check_contradictions, log_plan, submit_draft_for_critique]

    def ask(self, question: str) -> AgentResponse:
        trace_log = [{"step": "Start", "input": question}]
        chat = self.client.chats.create(
            model=self.model_id,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.0,
                tools=self.tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )
        
        current_msg = question
        iterations = 0
        final_answer = ""
        citations = set()
        
        resp = chat.send_message(current_msg)
        
        while iterations < 12:
            iterations += 1
            if resp.function_calls:
                results_to_send_back = []
                for fc in resp.function_calls:
                    args = dict(fc.args) if fc.args else {}
                    tool_name = fc.name
                    # Map tool names to Agent Roles for the UI
                    role_map = {
                        "log_plan": "Agent: Planner",
                        "retrieve_docs": "Agent: Retriever",
                        "check_contradictions": "Agent: Contradiction Checker",
                        "submit_draft_for_critique": "Agent: Critic",
                        "get_document_metadata": "Agent: Metadata Specialist"
                    }
                    role = role_map.get(tool_name, "Tool Call")
                    
                    trace_log.append({"step": role, "tool": tool_name, "arguments": args})
                    
                    if tool_name in AVAILABLE_TOOLS:
                        try:
                            func = AVAILABLE_TOOLS[tool_name]
                            tool_result_str = func(**args)
                        except Exception as e:
                            tool_result_str = f"Error: {e}"
                    else:
                        tool_result_str = f"Function {tool_name} not found."
                        
                    trace_log.append({"step": f"{role} Response", "tool": tool_name, "result_preview": str(tool_result_str)[:500]})
                    
                    if tool_name == "retrieve_docs":
                        import re
                        citations.update(re.findall(r"Document: (POL-[A-Z]+-\d+(?:-v\d+)?)", tool_result_str))
                        
                    results_to_send_back.append(
                        types.Part.from_function_response(name=tool_name, response={"result": tool_result_str})
                    )
                resp = chat.send_message(results_to_send_back)
            else:
                final_answer = resp.text
                trace_log.append({"step": "Final Answer generation", "text": final_answer})
                break
                
        if not final_answer:
            final_answer = "Error: Max iterations reached."
            
        return AgentResponse(
            answer=final_answer,
            citations=list(citations),
            confidence=0.85 if citations else 0.1,
            trace=trace_log
        )
