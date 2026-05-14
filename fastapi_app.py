
import sqlite3
import os
from fastapi import FastAPI
from pydantic import BaseModel
from litellm import completion
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import re

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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBE77WCd5DMI_kPpME4eQawnBXYHuaUtAo")
MEMBRANE_API_KEY = os.environ.get("MEMBRANE_API_KEY", "")

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
    import json
    
    # --- STEP 1: MEMBRANE DETERMINISTIC INTENT EXTRACTION ---
    membrane_prompt = """You are the Membrane Semantic Gate.
Your job is to extract rigid, unbiased search entities from the user's input.
Ignore conversational filler. Do not answer the question. Do not summarize.
Extract the target jurisdiction (City/County name) and 2 to 4 highly specific keywords or phrases (e.g. "police department", "interfund loan", "budget").

Return ONLY valid JSON in this exact format:
{
  "jurisdiction": "City Name",
  "keywords": ["keyword1", "keyword2"]
}
"""
    
    import requests
    try:
        headers = {
            "Authorization": f"Bearer {MEMBRANE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "membrane-engagement-layer",
            "messages": [
                {"role": "system", "content": membrane_prompt},
                {"role": "user", "content": req.jurisdiction + " " + req.query}
            ],
            "response_format": {"type": "json_object"}
        }
        mem_resp = requests.post(
            "https://membrane-api.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        if mem_resp.status_code == 200:
            mem_content = mem_resp.json()['choices'][0]['message']['content'].strip()
            if mem_content.startswith("```json"):
                mem_content = mem_content[7:-3]
            elif mem_content.startswith("```"):
                mem_content = mem_content[3:-3]
            extracted = json.loads(mem_content)
        else:
            print("Membrane API Error:", mem_resp.status_code, mem_resp.text)
            extracted = {}
        ext_jurisdiction = extracted.get("jurisdiction", req.jurisdiction)
        keywords = extracted.get("keywords", [])
        
        # If Membrane failed and ext_jurisdiction is Washington State, we need to extract from query instead.
        if mem_resp.status_code != 200:
            raise Exception("Membrane API Error")
            
    except Exception as e:
        print("Membrane Extraction Failed:", e)
        # Fallback to simple regex if Membrane fails
        stop_words = {"what", "why", "how", "when", "where", "who", "did", "does", "do", "has", "have", "had", "fail", "failed", "pass", "passed", "its", "their", "the", "a", "an", "is", "are", "was", "were", "audit", "audits", "findings", "finding", "about", "tell", "me", "show", "give", "can", "you", "city", "of", "county", "town", "district", "state", "washington"}
        words = re.findall(r'\b\w+\b', req.query.lower())
        keywords = list(set([w for w in words if w not in stop_words and len(w) > 2]))
        
        # In fallback, try to guess the jurisdiction from the query if req is generic
        ext_jurisdiction = req.jurisdiction
        if req.jurisdiction == "Washington State" and keywords:
             ext_jurisdiction = keywords[0].title() # Just guess the first keyword as the jurisdiction


    # --- STEP 2: DUMB QUERY (NO AGENTIC BIAS) ---
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    conn_muni = sqlite3.connect("municipal_intent.db")
    c_muni = conn_muni.cursor()
    
    sao_rows = []
    muni_rows = []
    
    if not keywords and ext_jurisdiction:
        # If Membrane found a jurisdiction but no keywords, we MUST filter by the jurisdiction!
        c.execute("SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings WHERE jurisdiction LIKE ? LIMIT 20", (f"%{ext_jurisdiction}%",))
        sao_rows = c.fetchall()
        try:
            c_muni.execute("SELECT jurisdiction, event_id, committee, meeting_date, key_action, vendor, dollar_amount, vote_outcome FROM merged_actions WHERE jurisdiction LIKE ? LIMIT 10", (f"%{ext_jurisdiction}%",))
            muni_rows = c_muni.fetchall()
        except:
            muni_rows = []
    elif not keywords and not ext_jurisdiction:
        # Extreme fallback
        c.execute("SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings LIMIT 20")
        sao_rows = c.fetchall()
        try:
            c_muni.execute("SELECT jurisdiction, event_id, committee, meeting_date, key_action, vendor, dollar_amount, vote_outcome FROM merged_actions LIMIT 10")
            muni_rows = c_muni.fetchall()
        except:
            muni_rows = []
    else:
        conditions = []
        params = []
        muni_cond = []
        muni_params = []
        for kw in keywords:
            conditions.append("(jurisdiction LIKE ? OR summary LIKE ? OR root_cause LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            muni_cond.append("(jurisdiction LIKE ? OR committee LIKE ? OR key_action LIKE ? OR vendor LIKE ?)")
            muni_params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            
        c.execute(f"SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings WHERE {' OR '.join(conditions)} LIMIT 20", params)
        sao_rows = c.fetchall()
        
        try:
            c_muni.execute(f"SELECT jurisdiction, event_id, committee, meeting_date, key_action, vendor, dollar_amount, vote_outcome FROM merged_actions WHERE {' OR '.join(muni_cond)} LIMIT 10", muni_params)
            muni_rows = c_muni.fetchall()
        except Exception as e:
            muni_rows = []

    conn.close()
    conn_muni.close()
    
    # --- STEP 3: SEMANTIC BOUNCER / NO-DATA GATE ---
    if not sao_rows and not muni_rows:
        async def fallback_generator():
            fallback_json = json.dumps({
                "narrative": f"I have searched the Policy Graph. While I understand you are asking about {ext_jurisdiction}, I do not currently have verified municipal documents or SAO findings expanding on this event yet. Assign me to monitor this topic and I will alert you when official documents are ingested.",
                "actions": ["Search another agency", "View statewide trends", "Analyze regional impacts"],
                "follow_up": "What other cities have records available?",
                "citations": []
            })
            yield f"data: {json.dumps({'chunk': fallback_json})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(fallback_generator(), media_type="text/event-stream")
    
    # --- STEP 4: FINAL STITCH (STRICT CONSTRAINT) ---
    context_lines = []
    for r in sao_rows:
        impact_str = f"${r[4]:,}" if r[4] else "None"
        arn = str(r[1]).replace('-', '')
        context_lines.append(f"SAO AUDIT (2024/2025) - Agency: {r[0]} | Report #: {r[1]} | Impact: {impact_str}\nSummary: {r[5]}\nRoot Cause: {r[6]}\nSource URL: https://portal.sao.wa.gov/ReportSearch/Home/ViewReportFile?arn={arn}&isFinding=false&sp=false\n---")
        
    for r in muni_rows:
        impact_str = f"${r[6]:,}" if r[6] else "None"
        vendor_str = r[5] if r[5] else "None"
        context_lines.append(f"CITY COUNCIL ACTION - Agency: {r[0]} | Date: {r[3]}\nAction: {r[4]}\nVendor: {vendor_str} | Impact: {impact_str}\nSource URL: https://{str(r[0]).lower().replace(' ', '')}.legistar.com/Calendar.aspx\n---")
        
    context_str = "\n".join(context_lines)
        
    system_prompt = f"""You are the Washington Policy Graph Oracle.
You provide deterministic, fact-based insights strictly derived from the provided database records.

USER INPUT: "{req.query}"

DATABASE CONTEXT:
{context_str}

CRITICAL CONSTRAINTS (THE "NO-PARROT" RULE):
1. DO NOT summarize or repeat the User's Input back to them.
2. YOU MUST READ THE ENTIRE DATABASE CONTEXT. If the user asks about a specific city (like Seattle) and that city is in the DATABASE CONTEXT, you MUST summarize those findings. DO NOT claim the city is missing if it is in the context.
3. List any other jurisdictions facing identical vulnerabilities found in the DATABASE CONTEXT.
4. If the user's input mentions an event or date you DO NOT have in the DATABASE CONTEXT, explicitly state that it is missing.
5. Return VALID JSON.

Return your response AS A VALID JSON OBJECT with the following exact keys:
{{
  "narrative": "Paragraph 1 (Historical context).\n\nParagraph 2 (Other jurisdictions).\n\nParagraph 3 (What is missing).",
  "actions": ["Information-seeking topic 1", "Information-seeking topic 2"],
  "follow_up": "Neutral question to explore more context",
  "citations": [
    {{"text": "Official Report Name/ID", "url": "https://..."}}
  ]
}}
"""

    try:
        response = completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.query}
            ],
            api_key=GEMINI_API_KEY,
            stream=True
        )
        
        async def event_generator():
            import json
            try:
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"data: {json.dumps({'chunk': content})}\n\n"
            except Exception as e:
                err = json.dumps({
                    "narrative": f"SYSTEM ERROR: The connection to the LLM Provider failed ({str(e)}). The API key might be expired.",
                    "actions": [],
                    "follow_up": "",
                    "citations": []
                })
                yield f"data: {json.dumps({'chunk': err})}\n\n"
            finally:
                yield "data: [DONE]\n\n"
            
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        async def err_generator():
            err_json = json.dumps({
                "narrative": f"SYSTEM ERROR (Outer): {str(e)}",
                "actions": [],
                "follow_up": "",
                "citations": []
            })
            yield f"data: {json.dumps({'chunk': err_json})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")



@app.get("/api/v1/feed/discoveries")
async def get_discoveries():
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    # Pull 5 high impact SAO audits
    c.execute("SELECT report_num, jurisdiction, category, dollar_impact, summary, type FROM findings WHERE dollar_impact > 100000 ORDER BY dollar_impact DESC LIMIT 5")
    sao_rows = c.fetchall()
    conn.close()
    
    conn_muni = sqlite3.connect("municipal_intent.db")
    c_muni = conn_muni.cursor()
    # Pull 3 high impact muni votes
    muni_rows = []
    try:
        c_muni.execute("SELECT event_id, jurisdiction, meeting_date, key_action, dollar_amount, committee FROM merged_actions WHERE dollar_amount > 1000000 ORDER BY meeting_date DESC LIMIT 3")
        muni_rows = c_muni.fetchall()
    except:
        pass
    conn_muni.close()
    
    cards = []
    
    for r in sao_rows:
        impact = f"${r[3]:,}"
        arn = str(r[0]).replace('-', '')
        jur = r[1]
        topic = 'schools' if 'School' in jur or 'Academy' in jur or 'District' in jur and 'Fire' not in jur else 'taxes'
        cards.append({
            "id": f"sao_{r[0]}",
            "topic": topic,
            "jurisdiction": jur,
            "title": f"{jur} Financial Audit",
            "subtitle": f"WA State Auditor // Published 2024-2025 // {r[2]}",
            "revelation_title": "Discovery Revelation:",
            "revelation_text": f"The audit reveals a {impact} issue. {r[4]}",
            "impact_text": f"This level of impact highlights critical needs for remediation within the {jur} jurisdiction to preserve public trust and financial stability.",
            "source_text": f"State Auditor Report #{r[0]} (2024/2025)",
            "source_url": f"https://portal.sao.wa.gov/ReportSearch/Home/ViewReportFile?arn={arn}&isFinding=false&sp=false",
            "followers": r[3] % 89 + 12
        })
        
    for r in muni_rows:
        impact = f"${r[4]:,}"
        jur_title = str(r[1]).title()
        cards.append({
            "id": f"muni_{r[0]}",
            "topic": 'taxes',
            "jurisdiction": jur_title,
            "title": f"{jur_title} Municipal Action",
            "subtitle": f"{r[5]} // Action Date: {r[2]}",
            "revelation_title": "Major Capital Authorization:",
            "revelation_text": f"The council processed a {impact} action: {r[3]}",
            "impact_text": f"Large appropriations of this scale directly impact the upcoming fiscal obligations and regional tax allocations for {r[1]}.",
            "source_text": f"City Council Meeting {r[2]}",
            "source_url": f"https://{str(r[1]).lower().replace(' ', '')}.legistar.com/Calendar.aspx",
            "followers": r[4] % 120 + 24
        })
        
    return {"discoveries": cards[:8]}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
