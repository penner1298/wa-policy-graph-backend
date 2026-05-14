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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

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
    # --- STEP 1: MEMBRANE ---
    ext_jurisdiction = req.jurisdiction
    keywords = []
    
    try:
        headers = {"Authorization": f"Bearer {MEMBRANE_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "membrane-engagement-layer",
            "messages": [{"role": "system", "content": "Extract jurisdiction and keywords JSON."}, {"role": "user", "content": req.query}],
            "response_format": {"type": "json_object"}
        }
        res = requests.post("https://membrane-api.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            parsed = res.json()["choices"][0]["message"]["content"]
            data = json.loads(parsed)
            ext_jurisdiction = data.get("jurisdiction", req.jurisdiction)
            keywords = data.get("keywords", [])
    except:
        stop_words = {"tell", "about", "seattle", "findings", "sfindings"}
        words = re.findall(r"\b\w+\b", req.query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        if "seattle" in req.query.lower():
            ext_jurisdiction = "Seattle"

    # --- STEP 2: QUERY ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    
    sao_rows = []
    if ext_jurisdiction and ext_jurisdiction != "Washington State":
        c.execute("SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings WHERE jurisdiction LIKE ? LIMIT 10", (f"%{ext_jurisdiction}%",))
        sao_rows = c.fetchall()
    
    if not sao_rows:
        c.execute("SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings LIMIT 10")
        sao_rows = c.fetchall()
    conn.close()

    # --- STEP 3: STITCH ---
    context_str = "\n".join([f"Agency: {r[0]} | Summary: {r[5]}" for r in sao_rows])
    system_prompt = f"Use this context to answer: {context_str}"

    async def event_generator():
        try:
            # Explicitly use openai/gpt-4o-mini for reliable testing
            response = completion(
                model="openai/gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
                api_key=OPENAI_API_KEY,
                stream=True
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'Error: {str(e)}'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/v1/feed/discoveries")
async def get_discoveries():
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT report_num, jurisdiction, category, dollar_impact, summary, type FROM findings WHERE dollar_impact > 100000 ORDER BY dollar_impact DESC LIMIT 5")
    sao_rows = c.fetchall()
    conn.close()
    
    cards = []
    for r in sao_rows:
        impact = f"${r[3]:,}"
        arn = str(r[0]).replace('-', '')
        cards.append({
            "id": f"sao_{r[0]}",
            "topic": "taxes",
            "jurisdiction": r[1],
            "title": f"{r[1]} Audit",
            "subtitle": f"WA State Auditor",
            "revelation_title": "Revelation:",
            "revelation_text": f"Impact: {impact}. {r[4]}",
            "impact_text": "Critical financial discovery.",
            "source_text": f"Report #{r[0]}",
            "source_url": f"https://portal.sao.wa.gov/ReportSearch/Home/ViewReportFile?arn={arn}&isFinding=false&sp=false",
            "followers": 10
        })
    return {"discoveries": cards}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
