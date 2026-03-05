from fastapi import FastAPI, Request
import requests as req
import json, hashlib, math, time, re, os

app = FastAPI(title="Cerebrus AIoT Gateway")

QDRANT_URL   = "http://qdrant.aiot.svc.cluster.local:6333"
TWIN_URL     = "http://digital-twin.aiot.svc.cluster.local:8001"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = "llama3.1-8b"
VECTOR_SIZE  = 64

SYSTEM_PROMPT = """You are Cerebrus AIoT — an intelligent industrial IoT monitoring assistant.
You analyze sensor data from factory machines (pumps, turbines, motors, compressors, conveyors, generators).

RULES:
- Answer in the SAME LANGUAGE as the user's question (Slovak, Czech, English, etc.)
- Be concise but thorough
- Always reference actual machine data provided in context
- Highlight critical issues first
- Give actionable recommendations
- Use units: temperature=°C, vibration=mm/s, pressure=bar, RPM
- Status levels: OK (green), WARNING (needs attention), CRITICAL (immediate action)
- If asked about trends, use the historical sensor data provided
- Format output clearly with headers and bullet points"""

def simple_embed(text):
    vec = []
    for i in range(VECTOR_SIZE):
        h = hashlib.md5(f"{text}{i}".encode()).hexdigest()
        vec.append((int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1)
    norm = math.sqrt(sum(x*x for x in vec))
    return [x/norm for x in vec]

def get_twin():
    try:
        r = req.get(f"{TWIN_URL}/twin", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def search_qdrant(query, limit=10):
    try:
        embedding = simple_embed(query)
        r = req.post(f"{QDRANT_URL}/collections/sensor_history/points/search",
            json={"vector": embedding, "limit": limit, "with_payload": True}, timeout=10)
        return r.json().get("result", [])
    except:
        return []

def build_context(query):
    """Build rich context from Digital Twin + Qdrant for LLM"""
    twin = get_twin()
    machines = twin.get("machines", {})
    summary = twin.get("summary", {})
    
    ok = summary.get("ok", 0)
    warn = summary.get("warning", 0)
    crit = summary.get("critical", 0)
    total = ok + warn + crit
    
    ctx = []
    ctx.append(f"=== FACTORY STATUS ===")
    ctx.append(f"Total: {total} machines | OK: {ok} | WARNING: {warn} | CRITICAL: {crit}")
    ctx.append(f"Critical machines: {', '.join(summary.get('critical_machines', []))}")
    ctx.append(f"Warning machines: {', '.join(summary.get('warning_machines', []))}")
    ctx.append("")
    
    ctx.append("=== ALL MACHINES ===")
    for mid in sorted(machines.keys()):
        m = machines[mid]
        mt = m.get("metrics", {})
        st = m.get("status", "").upper()
        viols = m.get("violations", [])
        line = f"{mid} ({m.get('machine_type','')}) [{st}] T={mt.get('temperature','-')}°C V={mt.get('vibration','-')}mm/s P={mt.get('pressure','-')}bar RPM={mt.get('rpm','-')} H={mt.get('humidity','-')}%"
        if viols:
            viol_str = "; ".join([f"{v['metric']}={v['value']} (limit={v.get('limit','')})" for v in viols])
            line += f" VIOLATIONS: {viol_str}"
        ctx.append(line)
    
    # Qdrant history
    results = search_qdrant(query, 5)
    if results:
        ctx.append("")
        ctx.append("=== RECENT SENSOR HISTORY (from vector DB) ===")
        for r in results:
            text = r.get("payload", {}).get("text", "")
            if text:
                ctx.append(text)
    
    return "\n".join(ctx)

def call_cerebras(system_msg, context, user_query):
    """Call Cerebras LLM API"""
    try:
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"MACHINE DATA:\n{context}\n\nUSER QUESTION: {user_query}"}
        ]
        r = req.post(CEREBRAS_URL,
            headers={
                "Authorization": f"Bearer {CEREBRAS_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": CEREBRAS_MODEL,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.3
            },
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"LLM Error ({r.status_code}): {r.text[:200]}"
    except Exception as e:
        return f"LLM Connection Error: {str(e)}"

def generate_analysis(query):
    """Generate intelligent analysis using Cerebras LLM"""
    context = build_context(query)
    answer = call_cerebras(SYSTEM_PROMPT, context, query)
    return answer

# === API Endpoints ===
@app.get("/")
def root():
    return {"service": "Cerebrus AIoT", "version": "3.0-LLM", "status": "running", "llm": CEREBRAS_MODEL}

@app.get("/health")
def health():
    try:
        r = req.get(f"{QDRANT_URL}/collections/sensor_history", timeout=5)
        info = r.json().get("result", {})
        twin = get_twin()
        return {"status": "healthy", "qdrant_points": info.get("points_count", 0),
                "machines": len(twin.get("machines", {})), "llm": CEREBRAS_MODEL}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.get("/search")
def search(q: str = "temperature", limit: int = 10):
    results = search_qdrant(q, limit)
    return {"query": q, "count": len(results),
            "results": [{"score": p.get("score"), "text": p.get("payload", {}).get("text", "")} for p in results]}

@app.get("/stats")
def stats():
    r = req.get(f"{QDRANT_URL}/collections/sensor_history", timeout=5)
    info = r.json().get("result", {})
    twin = get_twin()
    return {"points": info.get("points_count", 0), "machines": len(twin.get("machines", {})),
            "twin_summary": twin.get("summary", {})}

@app.get("/analyze")
def analyze(q: str = "summary"):
    return {"query": q, "analysis": generate_analysis(q)}

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "cerebrus-aiot", "object": "model"}]}

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    msgs = body.get("messages", [])
    user_msgs = [m for m in msgs if m.get("role") == "user"]
    q = user_msgs[-1]["content"].strip() if user_msgs else "summary"
    
    # Stream support check
    stream = body.get("stream", False)
    
    answer = generate_analysis(q)
    
    return {
        "id": f"cerebrus-{int(time.time())}",
        "object": "chat.completion",
        "model": "cerebrus-aiot",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
