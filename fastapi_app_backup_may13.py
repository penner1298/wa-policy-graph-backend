
import sqlite3
import os
from fastapi import FastAPI
from pydantic import BaseModel
from litellm import completion
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAO_DB_PATH = "sao_2024.db"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBBo12jBpSP67-m6OBKFUyUEGMnufHJaME")

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
    import re
    stop_words = {"what", "why", "how", "when", "where", "who", "did", "does", "do", "has", "have", "had", "fail", "failed", "pass", "passed", "its", "their", "the", "a", "an", "is", "are", "was", "were", "audit", "audits", "findings", "finding", "about", "tell", "me", "show", "give", "can", "you", "city", "of", "county", "town", "district"}
    
    raw_input = req.jurisdiction + " " + req.query
    words = re.findall(r'\b\w+\b', raw_input.lower())
    keywords = list(set([w for w in words if w not in stop_words and len(w) > 2]))
    
    conn = sqlite3.connect(SAO_DB_PATH)
    c = conn.cursor()
    
    conn_muni = sqlite3.connect("municipal_intent.db")
    c_muni = conn_muni.cursor()
    
    seattle_match = "seattle" in raw_input.lower()
    
    if seattle_match:
        c.execute("SELECT jurisdiction, report_num, type, category, dollar_impact, summary, root_cause FROM findings WHERE jurisdiction LIKE '%Seattle%' LIMIT 20")
        sao_rows = c.fetchall()
        try:
            c_muni.execute("SELECT jurisdiction, event_id, committee, meeting_date, key_action, vendor, dollar_amount, vote_outcome FROM merged_actions WHERE jurisdiction LIKE '%seattle%' LIMIT 10")
            muni_rows = c_muni.fetchall()
        except:
            muni_rows = []
    elif not keywords:
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

    
    if not sao_rows and not muni_rows:
        return {
            "narrative": f"As the Washington Policy Graph Oracle, I must inform you that I cannot answer your specific question regarding {req.jurisdiction} because there are no SAO findings or recent municipal records available in the database.",
            "actions": ["Search another agency", "View statewide trends", "Analyze regional impacts"],
            "follow_up": "What other cities have records available?",
            "citations": []
        }
    
    context_lines = []
    for r in sao_rows:
        impact_str = f"${r[4]:,}" if r[4] else "None"
        arn = str(r[1]).replace('-', '')
        # All SAO audits in this DB are from the 2024-2025 scraping batch.
        context_lines.append(f"SAO AUDIT (2024/2025) - Agency: {r[0]} | Report #: {r[1]} | Type: {r[2]} | Category: {r[3]} | Impact: {impact_str}\nSummary: {r[5]}\nRoot Cause: {r[6]}\nSource URL: https://portal.sao.wa.gov/ReportSearch/Home/ViewReportFile?arn={arn}&isFinding=false&sp=false\n---")
        
    for r in muni_rows:
        impact_str = f"${r[6]:,}" if r[6] else "None"
        vendor_str = r[5] if r[5] else "None"
        # Legistar meeting detail URL instead of legislation detail
        context_lines.append(f"CITY COUNCIL ACTION - Agency: {r[0]} | Event ID: {r[1]} | Committee: {r[2]} | Date: {r[3]}\nAction: {r[4]}\nVendor: {vendor_str} | Impact: {impact_str} | Vote: {r[7]}\nSource URL: https://{str(r[0]).lower().replace(' ', '')}.legistar.com/Calendar.aspx\n---")
        
    context_str = "\n".join(context_lines)
        
    system_prompt = f"""You are the Washington Policy Graph Oracle.
You provide deep insights on municipal audits and policies. You cross-reference Financial Audits with City Council Actions to find systemic connections.
The user is asking about: {req.jurisdiction}.
Answer the user's question: "{req.query}".

CORE DIRECTIVES:
1. VOICE & STRUCTURE: Use sharp, simple, punchy language. No "school report" academic fluff. Use short sentences. **IMPORTANT: Break your response into 2-3 readable paragraphs separated by double newlines (\n\n). Do NOT return a single wall of text.**
2. SYNTHESIS & RECENCY: You have access to both SAO Audits (2024-2025) and City Council Actions (which have exact dates). You MUST prioritize recency. Explicitly mention the year and date of the findings or council votes so the user knows how current the intelligence is. Cross-reference them when possible.
3. CITATIONS: You MUST cite the specific Agency and Report Number / Event ID for every fact. Use inline bracketed citations like [Seattle City Light #2024-001].
4. FORMAT: Return VALID JSON.
5. SUGGESTED ACTIONS: The `actions` array MUST contain neutral, information-seeking topics or questions to encourage deeper reading (e.g., "View contract details", "Explore compliance history", "Show breakdown of funds"). Do NOT suggest leading, political, or action-taking directives.
6. CITATIONS ARRAY: The `citations` field MUST be an array of objects containing a `text` label and a `url`. Extract the exact `Source URL` provided in the context below. Ensure it is a direct link.

Return your response AS A VALID JSON OBJECT with the following exact keys:
{{
  "narrative": "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3.",
  "actions": ["Information-seeking topic 1", "Information-seeking topic 2"],
  "follow_up": "Neutral question to explore more context",
  "citations": [
    {{"text": "Official Report Name/ID", "url": "https://..."}}
  ]
}}

Here is the context from the databases:
{context_str}
"""

    try:
        response = completion(
            model="gemini/gemini-3-flash-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.query}
            ],
            api_key=GEMINI_API_KEY
        )
        resp_text = response.choices[0].message.content
        import json
        try:
            clean_text = resp_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_text)
            actions = parsed.get("actions", [])
            defaults = ["View financial audit details", "Read meeting transcripts", "Check salary data", "Review grant compliance"]
            while len(actions) < 4 and defaults:
                d = defaults.pop(0)
                if d not in actions:
                    actions.append(d)
            
            return {
                "narrative": parsed.get("narrative", "Could not generate narrative."),
                "actions": actions[:4],
                "follow_up": parsed.get("follow_up", "What else would you like to know?"),
                "citations": parsed.get("citations", [])
            }
        except json.JSONDecodeError:
            return {
                "narrative": resp_text,
                "actions": ["Analyze financial audits", "Analyze meeting transcripts", "Analyze salary data", "Analyze grant compliance"],
                "follow_up": "Can you provide more details?",
                "citations": []
            }
    except Exception as e:
        return {
            "narrative": f"Error communicating with the Oracle model: {str(e)}",
            "actions": [],
            "follow_up": "",
            "citations": []
        }


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
