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
    # --- STEP 1: ENTENT EXTRACTION ---
    ext_jurisdiction = req.jurisdiction
    if "seattle" in req.query.lower():
        ext_jurisdiction = "Seattle"
    
    # --- STEP 2: DATABASE QUERY ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT jurisdiction, summary, report_num, type, category, dollar_impact, root_cause FROM findings WHERE jurisdiction LIKE ? LIMIT 10", (f"%{ext_jurisdiction}%",))
    sao_rows = c.fetchall()
    conn.close()

    context_lines = [f"Agency: {r[0]} | Report: {r[2]} | Impact: ${r[5]:,} | Summary: {r[1]}" for r in sao_rows]
    context_str = "\n".join(context_lines)
    system_prompt = f"You are the Washington Policy Graph Oracle. Use this context: {context_str}. Return JSON."

    async def event_generator():
        # Vertex AI / Google AI Studio handover is failing because of the "gemini/" prefix.
        # LiteLLM/Vertex requires "gemini/gemini-1.5-flash"
        model_name = "gemini/gemini-2.5-flash"
        api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyD85RsRSQF8fRT8IDJEMxvmWXHkhBI1x5Q")
        
        try:
            response = completion(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.query}],
                api_key=api_key,
                stream=True
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
