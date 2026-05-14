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

SAO_DB_PATH = "sao_2024.db"

class SynthesizeRequest(BaseModel):
    jurisdiction: str
    query: str

@app.post("/api/v1/oracle/synthesize")
async def synthesize(req: SynthesizeRequest):
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, summary FROM findings WHERE jurisdiction LIKE '%Seattle%' LIMIT 5")
    rows = c.fetchall()
    conn.close()

    context = "\\n".join([f"Agency: {r[0]} | Finding: {r[1]}" for r in rows])
    system_prompt = f"Summarize these findings: {context}"

    async def event_generator():
        # Vertex AI / Google AI Studio specific model string for LiteLLM
        # The correct format is gemini-1.5-flash (no gemini/ prefix if using standard litellm logic, or google/gemini-1.5-flash)
        model_name = "google/gemini-1.5-flash"
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
        
        try:
            response = completion(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
                api_key=GEMINI_KEY,
                stream=True
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\\n\\n"
        except Exception as e:
            err_json = json.dumps({
                "narrative": f"SYSTEM ERROR: {str(e)}",
                "actions": [],
                "follow_up": "",
                "citations": []
            })
            yield f"data: {json.dumps({'chunk': err_json})}\\n\\n"
        
        yield "data: [DONE]\\n\\n"

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
