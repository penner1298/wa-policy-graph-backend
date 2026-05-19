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
    # --- STEP 1: INTENT EXTRACTION ---
    # Very basic fallback for typos or missing jurisdiction in query
    ext_jurisdiction = req.jurisdiction
    
    # Simple extraction heuristic to catch missing apostrophes or common names
    raw_query = req.query.lower()
    
    # Common WA cities that might get typo'd
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
