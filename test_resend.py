"""Send real test emails to user's inbox."""
import os, sys, asyncio
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import importlib, emails
importlib.reload(emails)

TARGET = "suraganithanusri@gmail.com"

# Build a realistic sample order
sample_order = {
    "id": "test0001-0000-0000-0000-000000000001",
    "items": [
        {"name": "Arduino Uno R3 Compatible Board", "sku": "MCU-UNO-R3", "quantity": 1, "line_total": 499},
        {"name": "HC-SR04 Ultrasonic Distance Sensor", "sku": "SEN-HCSR04", "quantity": 2, "line_total": 258},
        {"name": "Jumper Wires - 40pcs Male-to-Male", "sku": "TOO-JW40", "quantity": 1, "line_total": 69},
    ],
    "subtotal": 826, "discount": 0, "shipping": 79, "tax": 149, "total": 1054,
    "address": {
        "full_name": "Thanusri Suragani", "phone": "+91 9999 999 999",
        "line1": "42 Maker Street", "line2": "Robotics Lab",
        "city": "Hyderabad", "state": "Telangana", "pincode": "500001", "country": "India",
    },
    "tracking_number": "IN-EH-2026-091234",
}

async def main():
    print(f"Provider active: {emails._resend is not None}")
    print(f"Sender: {emails.SENDER_EMAIL}")
    print(f"Target: {TARGET}\n")
    r1 = await emails.send_order_confirmation(sample_order, TARGET)
    print("1) Order confirmation ->", r1)
    r2 = await emails.send_shipping_notification(sample_order, TARGET)
    print("2) Shipping notification ->", r2)
    r3 = await emails.send_delivered_notification(sample_order, TARGET)
    print("3) Delivered notification ->", r3)

asyncio.run(main())
