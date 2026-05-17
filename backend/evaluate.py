import json
import os
import sys
from agent import PolicyAgent

EVAL_PATH = "../policy_corpus/eval_questions.json"
OUTPUT_PATH = "results.json"

def run_eval():
    if not os.path.exists(EVAL_PATH):
        print(f"Error: {EVAL_PATH} not found.")
        sys.exit(1)
        
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    questions = data.get("questions", [])
    
    agent = PolicyAgent()
    results = []
    
    print(f"Starting evaluation of {len(questions)} questions...")
    for idx, q in enumerate(questions):
        print(f"\n[{idx+1}/{len(questions)}] Evaluating Q{q['id']}: {q['question']}")
        
        reply = agent.ask(q["question"])
        
        results.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "expected_language": q.get("expected_language", "en"),
            "agent_answer": reply.answer,
            "citations": reply.citations,
            "confidence": reply.confidence,
            "trace": reply.trace
        })
        
        print(f"-> Answer: {reply.answer[:150]}...")
        
    # Write out
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2, ensure_ascii=False)
        
    print(f"\nEvaluation complete. Results saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_eval()
