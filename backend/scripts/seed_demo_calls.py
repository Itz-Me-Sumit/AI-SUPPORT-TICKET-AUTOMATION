"""Create sample tickets from simulated call transcripts on a running server.

Run from the backend folder:
    python scripts/seed_demo_calls.py https://3-107-146-58.sslip.io
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
GREETING = "assistant: Hello, thank you for calling TechNova support. How can I help you today?"

CALLS = [
    """user: Hi, my team has fifteen people. Which plan should we take?
assistant: The Pro plan supports up to 10 users, so for fifteen people the Business plan is the right fit. It costs 79 dollars per month and supports up to 50 users.
user: Does it include single sign on?
assistant: Yes, single sign-on is available on the Business plan. Is there anything else I can help you with?
user: No, that is all. Thank you.
assistant: Thanks for calling TechNova support. Have a great day.""",
    """user: Hello, I was charged twice for my Pro plan this month and I would like one payment refunded.
assistant: I am sorry about that. Duplicate charges are verified by our billing team, and approved refunds reach your original payment method in 5 to 7 business days. I cannot approve the refund myself.
user: This is the second time it has happened and I am really upset.
assistant: I understand. A billing specialist will review your case.
user: Okay, please make sure someone contacts me.""",
    """user: Hi, I just got an alert that someone logged into my account from another country. I did not do that.
assistant: Please reset your password right away and sign out of all devices from the Security settings. Suspected unauthorized access is treated as a critical issue and needs a human security specialist.
user: Okay, I will reset the password now. Please have someone look into it.
assistant: Understood. Is there anything else I can help you with?
user: No, thank you.""",
    """user: What are your support hours?
assistant: Live support is available Monday to Friday from 9 AM to 7 PM India Standard Time, and email support is available at all times.
user: Great, thanks.
assistant: You are welcome. Have a nice day.""",
    """user: I want to cancel my annual plan because the price is too high for us.
assistant: I am sorry to hear that. Annual customers can pause their subscription for up to 3 months, or you can downgrade to a cheaper plan at the start of the next billing period. The decision is always yours.
user: I will think about the pause option. How do I cancel if I decide to?
assistant: Open Settings, choose Billing, and select Cancel plan. Your plan stays active until the end of the period you already paid for.
user: Okay, thank you.""",
    """user: The mobile app keeps crashing every time I open the settings page.
assistant: First update the app to the latest version, then clear the app cache and restart your phone. If it still crashes, uninstall and reinstall the app.
user: I already reinstalled it and it still crashes with an error about a null pointer.
assistant: I am sorry about that. Please contact support with the error message and your phone model so that the team can look into it.
user: Okay, I will send those details.""",
    """user: Hello, mera Pro plan ka payment is mahine do baar kat gaya hai. Mujhe ek payment wapas chahiye.
assistant: Mujhe iske liye khed hai. Duplicate charge ko hamari billing team verify karti hai, aur approve hone ke baad refund 5 se 7 business days mein aapke original payment method par aa jata hai.
user: Theek hai, please jaldi dekhiye.
assistant: Zaroor, billing specialist aapke case ko dekhega. Aur kuch madad chahiye?
user: Nahi, dhanyavaad.""",
]


def send(transcript: str) -> None:
    execution = {
        "id": str(uuid.uuid4()),
        "status": "completed",
        "conversation_duration": 60,
        "transcript": GREETING + "\\n" + transcript,
    }
    request = urllib.request.Request(
        f"{BASE_URL}/api/voice/webhook",
        data=json.dumps(execution).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Voice-Secret": settings.voice_api_secret,
            "User-Agent": "seed-demo",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(response.status, response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(error.code, error.read().decode("utf-8"))


for number, transcript in enumerate(CALLS, start=1):
    print(f"Sending sample call {number}/{len(CALLS)}")
    send(transcript)
    time.sleep(8)

print("Done. Tickets appear in the dashboard in about a minute.")
