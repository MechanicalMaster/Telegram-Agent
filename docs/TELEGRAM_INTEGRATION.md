# Telegram Integration

This document guides you through setting up the Telegram integration for Ava agent.

## Prerequisites

Before you start, make sure you have:

1. Created a Telegram bot using BotFather
2. Obtained your Telegram Bot Token
3. Set up a server with a domain and SSL certificate (for production)

## Setting up a Telegram Bot

1. Open Telegram and search for the `BotFather` bot
2. Start a chat and send `/newbot` command
3. Follow the prompts to choose a name and username for your bot
4. BotFather will give you a token - keep this safe and add it to your `.env` file as `TELEGRAM_BOT_TOKEN`

## Local Development with ngrok

For local development, you can use ngrok to expose your local server to the internet:

1. Install ngrok if you haven't already
2. Run the Telegram service:
   ```bash
   make ava-run-telegram
   ```
3. In a new terminal, start ngrok:
   ```bash
   ngrok http 8081
   ```
4. Copy the HTTPS URL provided by ngrok (e.g., `https://your-ngrok-domain.ngrok.io`)
5. Register the webhook:
   ```bash
   make register-telegram-webhook WEBHOOK_URL=https://your-ngrok-domain.ngrok.io/telegram_webhook
   
## Production Deployment
gcloud config set compute/region asia-south1-a

gcloud config set project telegrambot-456606
For production:

gcloud config set compute/region asia-south1-a
gcloud auth configure-docker asia-south1-a-docker.pkg.dev -q 

gcloud artifacts repositories create ava-app --repository-format=docker \
    --location=asia-south1-a --description="Docker repository for Ava, the WhatsApp Agent" \
    --project=telegrambot-456606

1. Deploy the service to a server with a proper SSL certificate
2. Update your `.env` file with the production URL:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram_webhook
   ```
3. Run the service:
   ```bash
   make ava-run-telegram
   ```
4. Register the webhook:
   ```bash
   make register-telegram-webhook WEBHOOK_URL=https://your-domain.com/telegram_webhook
   ```

## Supported Features

The Telegram integration supports:

- Text messages
- Voice messages (automatic transcription)
- Images (with analysis)
- Receiving and responding with text, voice, and images

## Troubleshooting

If you encounter issues:

1. Check the logs for the Telegram service:
   ```bash
   docker compose logs telegram
   ```
2. Verify your webhook is registered correctly:
   ```bash
   curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq
   ```
3. Make sure your SSL certificate is valid and your domain is accessible

4. If you encounter an error saying "gunicorn: executable file not found in $PATH", ensure that gunicorn and uvicorn are installed in your Docker container. The Dockerfile.telegram should include:
   ```dockerfile
   # Install gunicorn explicitly
   RUN pip install gunicorn uvicorn
   ```

5. If you encounter a "ModuleNotFoundError: No module named 'ai_companion'" error, ensure that your Python path is set correctly in the Dockerfile:
   ```dockerfile
   # Make sure the package is properly installed
   RUN pip install -e .
   
   # Ensure app directory is in Python path
   ENV PYTHONPATH=/app
   ```

6. If you see "database is locked" errors in the logs, this means multiple processes are trying to access the SQLite database at the same time. Try these solutions:
   - Stop other services (like WhatsApp) that might be using the same database
   - Increase the SQLite timeout in the settings
   - Use a more robust database for production use

7. If ngrok shows internal server errors (500), check the following:
   - Verify your Telegram Bot Token is correctly set in the .env file
   - Check that you're using HTTPS for the webhook URL
   - Make sure your ngrok session is active and the correct port (8081) is being forwarded
   - Try restarting the Telegram service: `docker compose restart telegram`

8. If you've made changes to the Dockerfile, remember to rebuild the containers:
   ```bash
   docker compose down
   make ava-run-telegram
   ``` 
