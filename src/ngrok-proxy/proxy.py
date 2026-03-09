from fastapi import FastAPI, Request
import requests as req
import json, os

app = FastAPI(title="Ngrok RAG Proxy")
NGROK_URL = os.environ.get("NGROK_TARGET", "http://rag-api-svc.aiot.svc.cluster.local:7000")
MODEL_NAME = "ngrok-rag-aiot"

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "ngrok-proxy"}]}

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    body["model"] = "cerebrus-aiot"
    try:
        r = req.post(f"{NGROK_URL}/v1/chat/completions", json=body, timeout=60)
        data = r.json()
        data["model"] = MODEL_NAME
        return data
    except Exception as e:
        return {"id": "err", "object": "chat.completion", "model": MODEL_NAME,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": f"Ngrok proxy error: {e}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

@app.get("/health")
def health():
    return {"status": "ok", "target": NGROK_URL, "model": MODEL_NAME}
