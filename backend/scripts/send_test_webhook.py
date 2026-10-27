"""Send a fake 'completed' call webhook to a running backend.

Run from the backend folder while the server is running:
    python scripts/send_test_webhook.py
    python scripts/send_test_webhook.py https://your-tunnel.trycloudflare.com
"""
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

base_url = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"

execution = {
    "id": str(uuid.uuid4()),
    "status": "completed",
    "conversation_duration": 42,
    "transcript": (
        "assistant: Hello, thank you for calling TechNova support. How can I help you today?\n"
        "user: Hi, I was charged twice for my Pro plan this month and I want one payment refunded.\n"
        "assistant: I am sorry about that. How long does a refund usually take is something I can check for you.\n"
        "user: Yes please, and I am quite upset because this is the second time this happened.\n"
        "assistant: Approved refunds reach the original payment method in 5 to 7 business days.\n"
        "user: Okay, thanks."
    ),
}

request = urllib.request.Request(
    f"{base_url}/api/voice/webhook",
    data=json.dumps(execution).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "X-Voice-Secret": settings.voice_api_secret,
        "User-Agent": "webhook-test",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print(response.status, response.read().decode("utf-8"))
except urllib.error.HTTPError as error:
    print(error.code, error.read().decode("utf-8"))
