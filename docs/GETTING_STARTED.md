# Getting Started with Ava AI Companion

This guide will help you set up and run the Ava AI Companion, a modern conversational agent with robust memory, scheduling, and multi-modal capabilities, focused on Telegram as the main interface.

---

## 1. Clone the Repository

```bash
git clone https://github.com/MechanicalMaster/Telegram-Agent.git
cd Telegram-Agent
```

---

## 2. Install uv and Project Dependencies

We use [uv](https://docs.astral.sh/uv/getting-started/installation/) for fast, reliable Python dependency management.

```bash
uv venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
uv pip install -e .
```

---

## 3. Set Up Environment Variables

Copy the example environment file and fill in your API keys and tokens:

```bash
cp .env.example .env
```

Edit `.env` and set the following (see comments in the file for details):

- GROQ_API_KEY
- ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
- TOGETHER_API_KEY
- QDRANT_URL, QDRANT_API_KEY
- LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST (optional)
- TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL

**Note:** All reminders and time-based features use Indian Standard Time (IST, Asia/Kolkata).

---

## 4. Build and Run with Docker

To ensure a clean environment, you can remove all existing Docker images (optional):

```bash
docker rmi -f $(docker images -q)
```

Build a fresh Docker image for Ava:

```bash
docker build -t ai-companion:latest .
```

Start the services (Qdrant, Telegram bot, etc.):

```bash
docker-compose up
```

---

## 5. Set the Telegram Webhook

Set your Telegram webhook to your public endpoint (e.g., ngrok):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" -d "url=<YOUR_NGROK_URL>/telegram_webhook"
```

Replace `<YOUR_BOT_TOKEN>` and `<YOUR_NGROK_URL>` with your actual values.

---

## 6. Using the Reminder System

- Set reminders in natural language (e.g., "Remind me at 9pm tomorrow").
- Ava will extract the time expression and parse it using Python's `dateparser` and `pytz` libraries, always using IST.
- The confirmation message will include both the scheduled reminder time and the set time, both in IST.

---

## 7. Troubleshooting

- Ensure all required API keys and tokens are set in `.env`.
- If you encounter dependency issues, run `uv pip install -e .` again.
- For Docker issues, rebuild the image with `docker build -t ai-companion:latest .`.

---

## 8. Additional Notes

- All dependencies are managed in `pyproject.toml` and installed with `uv`.
- The Telegram bot is the main interface; WhatsApp and Chainlit are no longer supported.
- For advanced configuration, see the main [README.md](../README.md).

---

You're all set! Enjoy building and chatting with Ava.
