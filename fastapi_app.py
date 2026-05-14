import requests
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

class AssignRequest(BaseModel):
    name: str
    email: str
    jurisdiction: str
    query: str

@app.post("/api/v1/auth/assign")
async def assign_mission(req: AssignRequest):
    conn = sqlite3.connect("missions.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS missions (name TEXT, email TEXT, jurisdiction TEXT, query TEXT)")
    c.execute("INSERT INTO missions VALUES (?, ?, ?, ?)", (req.name, req.email, req.jurisdiction, req.query))
    conn.commit()
    conn.close()
    return {"status": "success"}

SAO_DB_PATH = "sao_2024.db"

class SearchQuery(BaseModel):
    query: str

class SynthesizeRequest(BaseModel):
    jurisdiction: str
    query: str

@app.get("/api/v1/search")
async def search_jurisdiction(q: str):
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT jurisdiction FROM findings WHERE jurisdiction LIKE ? LIMIT 5", (f"%{q}%",))
    rows = c.fetchall()
    conn.close()
    return {"results": [{"name": r[0], "type": "jurisdiction"} for r in rows]}

@app.post("/api/v1/oracle/synthesize")
async def synthesize(req: SynthesizeRequest):
    # --- STEP 1: INTENT EXTRACTION (HARD-CODED FALLBACK FOR STABILITY) ---
    ext_jurisdiction = req.jurisdiction
    if "seattle" in req.query.lower():
        ext_jurisdiction = "Seattle"
    
    # --- STEP 2: DATABASE QUERY ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, summary, report_num, type, category, dollar_impact, root_cause FROM findings WHERE jurisdiction LIKE ? LIMIT 10", (f"%{ext_jurisdiction}%",))
    sao_rows = c.fetchall()
    conn.close()

    # --- STEP 3: STITCH WITH GEMINI ---
    context_lines = []
    for r in sao_rows:
        context_lines.append(f"Agency: {r[0]} | Report: {r[2]} | Impact: ${r[5]:,} | Summary: {r[1]} | Root Cause: {r[6]}")
    
    context_str = "\n".join(context_lines)
    system_prompt = f"You are the Washington Policy Graph Oracle. Use this context: {context_str}. Return JSON with 'narrative', 'actions', 'follow_up', and 'citations'."

    async def event_generator():
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
        try:
            # The confirmed working model string for Gemini 1.5 Flash in LiteLLM is "gemini/gemini-1.5-flash"
            response = completion(
                model="gemini/gemini-1.5-flash",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
                api_key=GEMINI_KEY,
                stream=True
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\n\n"
        except Exception as e:
            err_json = json.dumps({"narrative": f"GEMINI ERROR: {str(e)}", "actions": [], "follow_up": "", "citations": []})
            yield f"data: {json.dumps({'chunk': err_json})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/v1/feed/discoveries")
async def get_discoveries():
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT report_num, jurisdiction, category, dollar_impact, summary, type FROM findings WHERE dollar_impact > 100000 ORDER BY dollar_impact DESC LIMIT 5")
    sao_rows = c.fetchall()
    conn.close()
    cards = [{"id": f"sao_{r[0]}", "topic": "taxes", "jurisdiction": r[1], "title": f"{r[1]} Audit", "subtitle": "WA State Auditor", "revelation_title": "Revelation:", "revelation_text": r[4], "impact_text": f"Impact: ${r[3]:,}", "source_text": f"Report #{r[0]}", "source_url": "#", "followers": 10} for r in sao_rows]
    return {"discoveries": cards}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
