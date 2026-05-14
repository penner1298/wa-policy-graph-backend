import requests
import sqlite3
import os
import json
import re
from fastapi import FastAPI
from pydantic import BaseModel
from litellm import completion
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAO_DB_PATH = "sao_2024.db"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

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

    try:
        resp = completion(
            model="openai/gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
            api_key=OPENAI_API_KEY
        )
        narrative = resp.choices[0].message.content
        return JSONResponse(content={
            "narrative": narrative,
            "actions": ["Action 1"],
            "follow_up": "Follow up?",
            "citations": []
        })
    except Exception as e:
        return JSONResponse(content={"narrative": f"Error: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
