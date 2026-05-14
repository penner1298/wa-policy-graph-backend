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
MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

class SynthesizeRequest(BaseModel):
    jurisdiction: str
    query: str

@app.post("/api/v1/oracle/synthesize")
async def synthesize(req: SynthesizeRequest):
    # --- STEP 1: QUERY (Manual Fallback First) ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, summary FROM findings WHERE jurisdiction LIKE '%Seattle%' LIMIT 5")
    rows = c.fetchall()
    conn.close()

    context = "\\n".join([f"Agency: {r[0]} | Finding: {r[1]}" for r in rows])
    system_prompt = f"Use context to answer. Context: {context}"

    async def gen():
        # Drip test
        yield f"data: {json.dumps({'chunk': 'Analysis starting... '})}\\n\\n"
        try:
            resp = completion(
                model="openai/gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
                api_key=OPENAI_API_KEY,
                stream=True
            )
            for chunk in resp:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'chunk': content})}\\n\\n"
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'Error: {str(e)}'})}\\n\\n"
        yield "data: [DONE]\\n\\n"
    
    return StreamingResponse(gen(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
