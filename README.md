---
title: Corporate Policy Agent
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---
# Meridian Consulting Agentic RAG Assistant

This prototype orchestrates an agentic AI system for Meridian Consulting, specifically designed to answer complex policy questions by leveraging advanced multi-step reasoning, supersession-aware retrieval, and contradiction detection.

## Architecture

```text
+-----------------------+        +--------------------------+
|      USER (Svelte UI) | <----> | FastAPI Backend (/chat)  |
+-----------------------+        +--------------------------+
                                              |
                                              v
+-----------------------+        +--------------------------+
|  Tool Execution Env   | <----> | Google GenAI Agent Loop  |
|  (Python Function)    |        | (Planner & Critique)     |
+-----------------------+        +--------------------------+
      |        |
      v        v
+----------+ +--------------+
| ChromaDB | | BM25 Index   | 
| (Dense)  | | (Keyword)    |
+----------+ +--------------+
```

1. **Ingestion Layer:** Parses Markdown, PDF (`PyMuPDF`), and DOCX (`python-docx`). Built recursively into chunks with metadata intact. Embeds chunks via `sentence-transformers` locally and keywords via `rank_bm25`, persisting to local disk.
2. **Orchestration Loop:** Uses `google-genai` native tool calling capabilities for maximum integration with Gemini models. The loop inherently plans, acts, and formulates using an automated iterative protocol. 
3. **Retrieval Tool:** By default, it aggressively filters out `superseded` documents unless explicitly instructed to include them. It cross-references keyword exact matches alongside densely encoded semantic proximities.
4. **Contradiction Tool:** Sub-agent prompt dynamically verifies contradicting signals across retrieved subsets.

## Model Choices & Reasoning

* **LLM**: configured to natively use the `GEMINI_MODEL` specified in your `.env` (e.g. `gemini-3-flash-preview` or `gemini-2.5-flash`). This allows you to evaluate across different Gemini tiers depending on local token allowances and free-tier scale.
* **Embeddings**: Local `all-MiniLM-L6-v2` (`sentence-transformers`). Relying entirely on Gemini Embeddings hits aggressive rate limits (15 RPM) during ingestion. A local embedding model provides free, robust dense vectors instantly.

## Running the Application

1. **Configuration**: Create a `.env` in the root directory (using `.env.example`).
   ```bash
   GEMINI_API_KEY="your_api_key"
   GEMINI_MODEL="gemini-3-flash-preview"
   ```
2. **Setup Backend**:
   Using `uv` for lightning-fast package management.
   ```bash
   cd backend
   uv sync
   # Or manually:
   # uv venv && source .venv/bin/activate
   # uv pip install -r pyproject.toml / deps
   uv run python ingest.py
   uv run uvicorn app:app --host 0.0.0.0 --port 8000
   ```
3. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Walk-Throughs

### Composition Handling
**Q:** "If I travel from Dubai to Abu Dhabi for a meeting with a UAE government client, what approvals and expense rules apply?"
**Agent Flow:** 
1. Calls `retrieve_docs(query="UAE government client meeting expenses and approvals")`.
2. Receives chunks from `POL-TRAVEL-003` (UAE Client Site Visits) and `POL-CLIENT-001` (Client Engagement).
3. The model observes specific regional directives and synthesizes both documents together, citing both IDs directly. 

### Contradiction Handling
**Q:** "How many days of paternity leave am I entitled to?"
**Agent Flow:**
1. Calls `retrieve_docs(query="paternity leave entitlement days")`.
2. Receives chunks from `POL-HR-002` (Parental Leave) and `POL-HR-003` (Benefits Summary).
3. The LLM processes both, but before replying, determines a contradiction exists (e.g. 10 days vs 14 days). It outputs: "Policy A indicates 10 days, but Policy B indicates 14 days. Please consult HR."

## Three Known Weaknesses & Solutions

1. **Weakness**: Heavy context payloads. Passing entire 2000-character doc samples into the contradiction tool wastes token window capacity and latency if scaling.
   **Fix**: Implement chunk-level precise claim extraction rather than sending raw chunks for comparison.
2. **Weakness**: Missing dynamic chunking strategies. Some policies have intense table formats (e.g., Hotel Cap Per Night) which recursive character chunkers might arbitrarily split, losing tabular meaning.
   **Fix**: Integrate unstructured.io or table-aware parsing for strict PDF hierarchies.
3. **Weakness**: Arabic retrieval quality. Since dense representations are `MiniLM-EN`, Arabic queries rely purely on the LM translating the question to English prior to the tool call, which misses BM25 token overlaps.
   **Fix**: Swap to a multilingual embedding model like `paraphrase-multilingual-MiniLM-L12-v2`.

## Next Steps (With more time)
- Migrate vector DB to managed services (PostgreSQL + pgvector).
- Create a dedicated UI flow showing visual contradiction flags.
- Introduce semantic chunk reranking utilizing a cross-encoder prior to sending to LLM.
