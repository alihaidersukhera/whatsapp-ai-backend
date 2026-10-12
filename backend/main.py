"""
WhatsApp AI Platform - FastAPI backend
- GET  /webhook  -> WhatsApp Cloud API verification
- POST /webhook  -> incoming WhatsApp messages (replies via BotBrain)
- POST /api/chat -> web-demo chat endpoint (used by dashboard/tests)
- GET  /api/conversations -> conversation log
Run: uvicorn backend.main:app --reload --port 8000   (from project root)
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from bot.brain import BotBrain

app = FastAPI(title="WhatsApp AI Platform")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "demo-verify-token")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")          # Meta Cloud API token
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")    # phone_number_id

brain = BotBrain(
    business_name=os.getenv("BUSINESS_NAME", "MuvMod Shoes"),
    owner_whatsapp=os.getenv("OWNER_WHATSAPP", "03278369194"),
)


@app.get("/")
def root():
    return {"ok": True, "service": "whatsapp-ai-platform"}


# ---------- WhatsApp Cloud API webhook ----------
@app.get("/webhook")
def verify_webhook(request: Request):
    """Meta calls this once to verify the webhook URL."""
    params = dict(request.query_params)
    if (params.get("hub.mode") == "subscribe"
            and params.get("hub.verify_token") == VERIFY_TOKEN):
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("verification failed", status_code=403)


@app.post("/webhook")
async def receive_whatsapp(request: Request):
    """Receives incoming WhatsApp messages, replies through the bot brain."""
    try:
        data = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid json"}

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("type") != "text":
                    continue
                sender = msg.get("from", "unknown")
                text = msg.get("text", {}).get("body", "")
                reply = brain.handle_message(text, user_id=sender)
                _send_whatsapp(sender, reply)
    return {"ok": True}


def _send_whatsapp(to, text):
    """Sends a WhatsApp message via Meta Cloud API. Demo mode: just logs."""
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID):
        print(f"[DEMO SEND -> {to}]: {text[:120]}")
        return
    import urllib.request, json
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                 "Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"[WHATSAPP SEND FAILED]: {e}")


# ---------- demo / dashboard APIs ----------
@app.post("/api/chat")
def demo_chat(payload: dict):
    reply = brain.handle_message(
        payload.get("message", ""), payload.get("user_id", "demo-user")
    )
    return {"reply": reply}


@app.get("/api/conversations")
def conversations():
    return {"count": len(brain.conversation_log),
            "items": brain.conversation_log[-100:]}
