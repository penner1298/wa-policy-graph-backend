import sqlite3
import os
import json
import re
from fastapi import FastAPI
from pydantic import BaseModel
from litellm import completion
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAO_DB_PATH = "sao_2024.db"

class SynthesizeRequest(BaseModel):
    jurisdiction: str
    query: str

@app.post("/api/v1/oracle/synthesize")
async def synthesize(req: SynthesizeRequest):
    # --- STEP 1: INTENT EXTRACTION (MEMBRANE API) ---
    ext_jurisdiction = req.jurisdiction
    keywords = []
    
    # Try the Membrane API first (Deterministic Semantic Gate)
    MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY", "")
    if MEMBRANE_API_KEY:
        try:
            membrane_prompt = """You are the Membrane Semantic Gate. Extract jurisdiction and 2-4 keywords. Return JSON: {"jurisdiction": "City", "keywords": ["kw1", "kw2"]}"""
            headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "membrane-engagement-layer",
                "messages": [{"role": "system", "content": membrane_prompt}, {"role": "user", "content": req.query}],
                "response_format": {"type": "json_object"}
            }
            import requests
            res = requests.post("https://membrane-api.com/v1/chat/completions", headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                parsed = json.loads(res.json()["choices"][0]["message"]["content"])
                ext_jurisdiction = parsed.get("jurisdiction", req.jurisdiction)
                keywords = parsed.get("keywords", [])
        except Exception as e:
            print("Membrane API failed, falling back to heuristics:", e)
            pass

    # Fallback to simple extraction heuristic if Membrane didn't yield a jurisdiction change
    if ext_jurisdiction == req.jurisdiction:
        raw_query = req.query.lower()
        wa_cities = ["seattle", "tacoma", "bellevue", "spokane", "everett", "kent", "renton", "yakima"]
        for city in wa_cities:
            if city in raw_query:
                ext_jurisdiction = city.title()
                break

    # Remove "'s" or "s" for exact DB matching
    ext_jurisdiction = re.sub(r"[']?s$", "", ext_jurisdiction.strip())

    # --- STEP 2: DATABASE QUERY ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    
    query_str = "SELECT jurisdiction, summary, report_num, type, category, dollar_impact, root_cause FROM findings WHERE 1=1"
    params = []
    if ext_jurisdiction and ext_jurisdiction != "Washington State":
        query_str += " AND jurisdiction LIKE ?"
        params.append(f"%{ext_jurisdiction}%")
        
    if keywords:
        kw_clauses = ["summary LIKE ?" for _ in keywords]
        query_str += f" AND ({' OR '.join(kw_clauses)})"
        params.extend([f"%{kw}%" for kw in keywords])
        
    query_str += " LIMIT 10"
    
    c.execute(query_str, params)
    sao_rows = c.fetchall()
    
    # Broad fallback if Membrane found keywords but missed the exact jurisdiction string
    if not sao_rows and ext_jurisdiction and ext_jurisdiction != "Washington State":
        c.execute("SELECT jurisdiction, summary, report_num, type, category, dollar_impact, root_cause FROM findings WHERE jurisdiction LIKE ? LIMIT 10", (f"%{ext_jurisdiction}%",))
        sao_rows = c.fetchall()
        
    conn.close()

    context_lines = []
    for r in sao_rows:
        impact = f"${r[5]:,}" if r[5] else "None"
        context_lines.append(f"Agency: {r[0]} | Report: {r[2]} | Impact: {impact} | Summary: {r[1]}")
        
    context_str = "\n".join(context_lines)
    
    if not sao_rows:
        context_str = f"No findings currently in the database for {ext_jurisdiction}."

    # --- STEP 3: SYNTHESIS ---
    system_prompt = f"""You are the Washington Policy Graph Oracle.
You provide deep insights on municipal audits and policies.
The user is asking about: {ext_jurisdiction}.

CORE DIRECTIVES:
1. VOICE & STRUCTURE: Use sharp, simple, punchy language. Break your response into 2-3 readable paragraphs.
2. SYNTHESIS: Use the provided context to answer the user's question. If the context says 'No findings', explain that.
3. FORMAT: You MUST return ONLY valid JSON matching this exact schema:
{{
  "narrative": "Your summarized response here.",
  "citations": [
    {{"text": "Agency - Report #", "url": "https://portal.sao.wa.gov/"}}
  ],
  "actions": [
    "View financial audit details",
    "Read meeting transcripts"
  ]
}}

CONTEXT:
{context_str}
"""

    async def event_generator():
        # LiteLLM/Vertex requires "gemini/gemini-2.5-flash"
        model_name = "gemini/gemini-2.5-flash"
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
        try:
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": req.query}
                ],
                api_key=api_key,
                stream=True,
                response_format={"type": "json_object"}
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'chunk': json.dumps({'narrative': f'TECHNICAL ERROR: {str(e)}'})})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
