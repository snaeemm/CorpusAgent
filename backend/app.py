from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime

from agent import PolicyAgent, AgentResponse

app = FastAPI(title="Meridian API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = PolicyAgent()
LOGS_FILE = "logs.json"

class ChatRequest(BaseModel):
    question: str

@app.post("/api/chat", response_model=AgentResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        response = agent.ask(req.question)
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": req.question,
            "answer": response.answer,
            "citations": response.citations,
            "confidence": response.confidence,
            "trace": response.trace
        }
        logs = []
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, "r") as f:
                    logs = json.load(f)
            except:
                pass
        logs.insert(0, log_entry) 
        with open(LOGS_FILE, "w") as f:
            json.dump(logs[:50], f) 
            
        return response
    except Exception as e:
        if "429" in str(e) or "exhausted" in str(e).lower() or "quota" in str(e).lower():
            return AgentResponse(
                answer="⚠️ **API Rate Limit Exceeded:** The free-tier Gemini API enforces strict requests-per-minute quotas. Please wait ~30 seconds before asking another query.",
                citations=[],
                confidence=0.0,
                trace=[{"step": "Error", "text": "429 RESOURCE_EXHAUSTED Exception intercepted gracefully."}]
            )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
