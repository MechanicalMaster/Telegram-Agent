import os
import sys
import asyncio
from datetime import datetime
from ai_companion.modules.schedules.reminder import get_due_reminders, mark_reminder_sent

import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("TELEGRAM_BOT_TOKEN not set in environment.")
    sys.exit(1)

async def send_telegram_message(chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=data)
        result = resp.json()
        return result.get("ok", False)

async def main():
    due_reminders = get_due_reminders(window_minutes=5)
    for reminder_id, chat_id, reminder_text, reminder_time in due_reminders:
        # Format the reminder message
        msg = f"⏰ Reminder: {reminder_text} (scheduled for {reminder_time})"
        sent = await send_telegram_message(chat_id, msg)
        if sent:
            mark_reminder_sent(reminder_id)
            print(f"Sent reminder to {chat_id}: {reminder_text} at {reminder_time}")
        else:
            print(f"Failed to send reminder to {chat_id}: {reminder_text} at {reminder_time}")

if __name__ == "__main__":
    asyncio.run(main())
