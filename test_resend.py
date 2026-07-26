"""Quick Resend test - verifies API key + sender work."""
import os, sys, asyncio
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
# Reload emails module with fresh env
import importlib
import emails
importlib.reload(emails)

async def main():
    # Get target email from arg or default
    target = sys.argv[1] if len(sys.argv) > 1 else "delivered@resend.dev"
    print(f"Provider active: {emails._resend is not None}")
    print(f"Sender: {emails.SENDER_EMAIL}")
    print(f"Target: {target}")
    res = await emails.send_email(target, "ElectronicHub · Test",
        emails._wrap("<h1 style='color:#0F172A'>Resend is live ✓</h1><p>If you see this, real emails are on.</p>"))
    print("Result:", res)

asyncio.run(main())
