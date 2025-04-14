<p align="center">
    <h1 align="center">🤖 Telegram Agent 🤖</h1>
    <h3 align="center">A Modern Conversational AI Agent</h3>
</p>

## Table of Contents

- [Overview](#overview)
- [Who is this for?](#who-is-this-for)
- [Features](#features)
- [Getting Started](#getting-started)
- [Reminder System & Time Handling](#reminder-system--time-handling)
- [Docker & Deployment](#docker--deployment)
- [Tech Stack](#tech-stack)
- [Contributors](#contributors)
- [License](#license)

## Overview

Ava is an advanced AI agent inspired by the film [Ex Machina](https://www.imdb.com/es-es/title/tt0470752/), designed to interact with users via Telegram. Ava can chat, understand voice, process images, and manage reminders with robust time handling in Indian Standard Time (IST).

## Who is this for?

This project is supposed to be demo of the original eva bot, heavily modified to work with Telegram and additinal features like observability via Langfuse.

## Features

- **Telegram Bot Interface**: Chat with Ava directly on Telegram.
- **Voice & Image Understanding**: Send voice notes and images for Ava to process.
- **Reminders with Natural Language**: Set reminders using natural language (e.g., "Remind me at 9pm tomorrow").
- **IST Time Handling**: All reminders and time-based features use Indian Standard Time (IST).
- **LangGraph Workflow**: Modular, extensible workflow for message processing, memory, and scheduling.
- **Cloud-Ready**: Easily deployable with Docker and Google Cloud Run.

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/MechanicalMaster/Telegram-Agent.git
   cd Telegram-Agent
   ```

2. **Install uv and dependencies**
   - Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
   - Create a virtual environment and install dependencies:
     ```bash
     uv venv .venv
     source .venv/bin/activate
     uv pip install -e .
     ```

3. **Set up environment variables**
   - Copy `.env.example` to `.env` and fill in your API keys and tokens.

4. **Run with Docker**
   - Build a fresh Docker image:
     ```bash
     docker build -t ai-companion:latest .
     ```
   - Run the container (see `docker-compose.yml` for service orchestration).

5. **Start the Telegram Bot**
   - Set your webhook using your ngrok/public URL and Telegram bot token.

## Reminder System & Time Handling

- **Natural Language Extraction**: The LLM extracts the raw time expression (e.g., "9.00pm", "tomorrow morning") and reminder text from the user's message.
- **Python Time Parsing**: The backend uses the `dateparser` and `pytz` libraries to robustly parse the time expression, always using IST (`Asia/Kolkata`).
- **Confirmation Message**: When a reminder is set, the confirmation message includes both the scheduled reminder time and the exact time the reminder was set, both in IST.
- **Dependencies**: All time parsing is handled in Python, not by the LLM, ensuring reliability for Indian users.

## Docker & Deployment

- **Dependencies**: All Python dependencies are managed in `pyproject.toml` and installed with `uv`.
- **Building**: Use the provided `Dockerfile` to build the image. All dependencies, including `dateparser` and `pytz`, are installed automatically.
- **Running**: Use `docker-compose.yml` for multi-service orchestration (e.g., Qdrant, Telegram bot).

## Tech Stack

| Technology         | Description                                                      |
|--------------------|------------------------------------------------------------------|
| Groq               | Fast LLM inference for chat and vision models                    |
| Qdrant             | Vector database for long-term memory                             |
| FastAPI            | Backend API (for WhatsApp, if enabled)                           |
| LangGraph          | Modular workflow orchestration                                   |
| ElevenLabs         | Text-to-speech (TTS)                                             |
| Together AI        | Image generation                                                 |
| dateparser, pytz   | Robust natural language time parsing in IST                      |


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
