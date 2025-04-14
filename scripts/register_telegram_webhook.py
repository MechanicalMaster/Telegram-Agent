import argparse
import os
import requests
from dotenv import load_dotenv

def register_webhook(webhook_url):
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return False
    
    set_webhook_url = f"https://api.telegram.org/bot{token}/setWebhook"
    
    response = requests.post(
        set_webhook_url,
        json={
            "url": webhook_url,
            "allowed_updates": ["message"]
        }
    )
    
    result = response.json()
    
    if result.get("ok"):
        print(f"Webhook set successfully to {webhook_url}")
        return True
    else:
        print(f"Failed to set webhook: {result}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register Telegram webhook URL")
    parser.add_argument("webhook_url", help="The HTTPS URL for the webhook")
    args = parser.parse_args()
    
    register_webhook(args.webhook_url) 