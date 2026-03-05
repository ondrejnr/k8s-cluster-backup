import json, time, logging, threading, hashlib
import requests, redis
from flask import Flask, jsonify, request
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag-worker")
REDIS_HOST   = "redis-master.aiot.svc.cluster.local"
CEREBRUS_URL = "http://api-gateway.aiot.svc.cluster.local:8080"
POLL_INTERVAL = 60
ANSWER_TTL    = 300
rd = redis.Redis(host=REDIS_HOST, port=6379, db=3, decode_responses=True)
app = Flask(__name__)
stats = {"queries":0, "bg_cycles":0, "cache_hits":0, "start_time": time.time()}
stats_lock = threading.Lock()
def inc(key, n=1):
    with stats_lock: stats[key] = stats.get(key, 0) + n
def call_cerebrus(query):
    try:
        r = requests.post(f"{CEREBRUS_URL}/v1/chat/completions",
            json={"model":"cerebrus-aiot","messages":[{"role":"user","content":query}]}, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.error(f"Cerebrus error: {e}")
    return None
def run_background():
    while True:
        try:
            inc("bg_cycles")
            analysis = call_cerebrus("summary")
            if analysis:
                try: health = requests.get(f"{CEREBRUS_URL}/health", timeout=5).json()
                except: health = {}
                payload = json.dumps({"analysis": analysis, "qdrant_points": health.get("qdrant_points",0),
                    "machines": health.get("machines",0), "timestamp": time.time()})
                rd.setex("rag:latest_analysis", ANSWER_TTL, payload)
                log.info(f"[BG] Updated via Cerebrus ({len(analysis)} chars)")
            else:
                log.warning("[BG] No response from Cerebrus")
        except Exception as e:
            log.error(f"BG error: {e}")
        time.sleep(POLL_INTERVAL)
@app.route("/")
def root():
    return jsonify({"service": "RAG Worker", "mode": "cerebrus-backend", "status": "running"})
@app.route("/status")
def status():
    c = rd.get("rag:latest_analysis")
    d = json.loads(c) if c else None
    return jsonify(d) if d else (jsonify({"error": "No data yet"}), 404)
@app.route("/v1/chat/completions", methods=["POST"])
def chat():
    msgs = (request.json or {}).get("messages", [])
    user = [m for m in msgs if m.get("role") == "user"]
    q = user[-1]["content"].strip() if user else "summary"
    cache_key = f"rag:chat:{hashlib.sha256(q.encode()).hexdigest()[:16]}"
    cached = rd.get(cache_key)
    if cached:
        inc("cache_hits"); content = cached
    else:
        content = call_cerebrus(q) or "System starting up..."
        if content: rd.setex(cache_key, ANSWER_TTL, content)
    inc("queries")
    return jsonify({"id": f"rag-{int(time.time())}", "object": "chat.completion", "model": "cerebrus-aiot",
        "choices": [{"index":0, "message": {"role":"assistant","content":content}, "finish_reason":"stop"}],
        "usage": {"prompt_tokens":0, "completion_tokens":0, "total_tokens":0}})
@app.route("/v1/models")
def models():
    return jsonify({"object": "list", "data": [{"id": "cerebrus-aiot", "object": "model"}]})
@app.route("/stats")
def stats_ep():
    with stats_lock:
        return jsonify({**stats, "uptime_s": int(time.time() - stats["start_time"])})
threading.Thread(target=run_background, daemon=True).start()
log.info("RAG Worker v5 — Cerebrus backend on port 7000")
app.run(host="0.0.0.0", port=7000)
