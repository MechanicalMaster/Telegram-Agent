import logging
import os
from io import BytesIO
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Request, Response
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_companion.graph import graph_builder
from ai_companion.modules.image import ImageToText
from ai_companion.modules.speech import SpeechToText, TextToSpeech
from ai_companion.settings import settings
from ai_companion.utils.langfuse import get_langfuse_handler

logger = logging.getLogger(__name__)

# Global module instances
speech_to_text = SpeechToText()
text_to_speech = TextToSpeech()
image_to_text = ImageToText()

# Router for Telegram responses
telegram_router = APIRouter()

# Telegram API credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Check if the token is available
if not TELEGRAM_BOT_TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN is not set. Telegram functionality will be limited.")

@telegram_router.api_route("/telegram_webhook", methods=["POST", "GET"])
async def telegram_handler(request: Request) -> Response:
    """Handles incoming messages from Telegram Bot API."""
    
    # Handle webhook verification
    if request.method == "GET":
        logger.info("Handling GET request for webhook verification")
        return Response(content="Telegram webhook endpoint is active", status_code=200)
    
    # Check if token is configured
    if not TELEGRAM_BOT_TOKEN:
        error_msg = "Telegram Bot Token is not configured. Please set TELEGRAM_BOT_TOKEN in your .env file."
        logger.error(error_msg)
        return Response(content=error_msg, status_code=500)
    
    try:
        logger.info("Received webhook request from Telegram")
        data = await request.json()
        logger.info(f"Webhook data: {data}")

        # Initialize Langfuse CallbackHandler for tracing
        langfuse_handler = get_langfuse_handler()
        
        # Handle Telegram update
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            session_id = str(chat_id)  # Use chat_id as session identifier
            logger.info(f"Processing message from chat ID: {chat_id}")

            # Blocklist check
            import sqlite3
            BLOCKLIST_DB = "admin_blocklist.db"
            conn = sqlite3.connect(BLOCKLIST_DB)
            c = conn.cursor()
            c.execute("SELECT 1 FROM blocked_users WHERE telegram_id = ?", (str(chat_id),))
            is_blocked = c.fetchone() is not None
            conn.close()
            if is_blocked:
                logger.info(f"Blocked user {chat_id} attempted to send a message. Ignoring.")
                return Response(content="User is blocked.", status_code=200)
            
            # Get user message content based on type
            content = ""
            
            # Handle text messages
            if "text" in message:
                content = message["text"]
                logger.info(f"Received text message: {content}")
            
            # Handle voice messages
            elif "voice" in message:
                logger.info("Received voice message, processing...")
                content = await process_voice_message(message["voice"]["file_id"])
                logger.info(f"Transcribed voice message: {content}")
            
            # Handle photo messages
            elif "photo" in message:
                logger.info("Received photo message, processing...")
                # Get the highest resolution photo
                photo = message["photo"][-1]  
                photo_file_id = photo["file_id"]
                
                # Get caption if any
                content = message.get("caption", "")
                
                # Download and analyze image
                image_bytes = await download_file(photo_file_id)
                try:
                    logger.info("Analyzing image with vision model...")
                    description = await image_to_text.analyze_image(
                        image_bytes,
                        "Please describe what you see in this image in the context of our conversation.",
                    )
                    content += f"\n[Image Analysis: {description}]"
                    logger.info(f"Image analysis result: {description}")
                except Exception as e:
                    logger.warning(f"Failed to analyze image: {e}")
            else:
                logger.warning(f"Unsupported message type received: {message.get('type', 'unknown')}")
                return Response(content="Unsupported message type", status_code=200)
            
            # Process message through the graph agent
            logger.info("Processing message through graph agent...")
            try:
                async with AsyncSqliteSaver.from_conn_string(settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
                    graph = graph_builder.compile(checkpointer=short_term_memory)
                    await graph.ainvoke(
                        {"messages": [HumanMessage(content=content)], "chat_id": session_id},
                        {
                            "configurable": {"thread_id": session_id},
                            "callbacks": [langfuse_handler],
                            "run_name": "telegram_message",
                            "metadata": {
                                "langfuse_session_id": session_id,
                                "langfuse_user_id": str(chat_id),
                                "raw_update": data,
                            },
                        },
                    )
                    
                    # Get the workflow type and response from the state
                    output_state = await graph.aget_state(config={"configurable": {"thread_id": session_id}})
                logger.info("Graph processing completed successfully")
            except Exception as e:
                logger.error(f"Error in graph processing: {str(e)}", exc_info=True)
                return Response(content="Error processing message through AI", status_code=500)
                
            workflow = output_state.values.get("workflow", "conversation")
            response_message = output_state.values["messages"][-1].content
            logger.info(f"Response workflow: {workflow}, message: {response_message[:50]}...")
            
            # Handle different response types based on workflow
            logger.info(f"Sending {workflow} response to chat ID: {chat_id}")
            success = False
            try:
                if workflow == "audio":
                    audio_buffer = output_state.values["audio_buffer"]
                    success = await send_voice_message(chat_id, audio_buffer, response_message)
                elif workflow == "image":
                    image_path = output_state.values["image_path"]
                    with open(image_path, "rb") as f:
                        image_data = f.read()
                    success = await send_photo_message(chat_id, image_data, response_message)
                else:
                    success = await send_text_message(chat_id, response_message)
            except Exception as e:
                logger.error(f"Error sending response: {str(e)}", exc_info=True)
                return Response(content=f"Error sending response: {str(e)}", status_code=500)
            
            if not success:
                logger.error("Failed to send message to Telegram API")
                return Response(content="Failed to send message", status_code=500)
            
            logger.info("Message processed and response sent successfully")
            return Response(content="Message processed", status_code=200)
        
        logger.warning("No 'message' field found in the Telegram update")
        return Response(content="No message in update", status_code=200)
    
    except Exception as e:
        logger.error(f"Unhandled error in telegram_handler: {str(e)}", exc_info=True)
        return Response(content=f"Internal server error: {str(e)}", status_code=500)

async def download_file(file_id: str) -> bytes:
    """Download file from Telegram."""
    file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    params = {"file_id": file_id}
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Getting file info for file ID: {file_id}")
            response = await client.get(file_info_url, params=params)
            response.raise_for_status()
            file_info = response.json()
            
            if not file_info.get("ok"):
                error_msg = f"Failed to get file info: {file_info}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            logger.info(f"Downloading file from path: {file_path}")
            
            file_response = await client.get(file_url)
            file_response.raise_for_status()
            return file_response.content
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when downloading file: {e.response.status_code} {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        raise

async def process_voice_message(voice_file_id: str) -> str:
    """Download and transcribe voice message."""
    try:
        logger.info(f"Processing voice message with file ID: {voice_file_id}")
        voice_bytes = await download_file(voice_file_id)
        
        # Prepare for transcription
        voice_buffer = BytesIO(voice_bytes)
        voice_buffer.seek(0)
        voice_data = voice_buffer.read()
        
        logger.info("Transcribing voice message")
        transcript = await speech_to_text.transcribe(voice_data)
        logger.info(f"Transcription result: {transcript}")
        return transcript
    except Exception as e:
        logger.error(f"Error processing voice message: {str(e)}", exc_info=True)
        raise

async def send_text_message(chat_id: int, text: str) -> bool:
    """Send text message to Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        logger.info(f"Sending text message to chat ID {chat_id}: {text[:50]}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"Failed to send text message: {result}")
                return False
                
            logger.info("Text message sent successfully")
            return True
    except Exception as e:
        logger.error(f"Error sending text message: {str(e)}", exc_info=True)
        return False

async def send_photo_message(chat_id: int, photo_data: bytes, caption: Optional[str] = None) -> bool:
    """Send photo message to Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    files = {"photo": photo_data}
    data = {"chat_id": chat_id}
    
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    
    try:
        logger.info(f"Sending photo message to chat ID {chat_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, files=files)
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"Failed to send photo message: {result}")
                return False
                
            logger.info("Photo message sent successfully")
            return True
    except Exception as e:
        logger.error(f"Error sending photo message: {str(e)}", exc_info=True)
        return False

async def send_voice_message(chat_id: int, voice_data: bytes, caption: Optional[str] = None) -> bool:
    """Send voice message to Telegram chat (with optional follow-up text message for caption)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    
    files = {"voice": voice_data}
    data = {"chat_id": chat_id}
    
    try:
        logger.info(f"Sending voice message to chat ID {chat_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, files=files)
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"Failed to send voice message: {result}")
                return False
                
            success = True
            logger.info("Voice message sent successfully")
            
            # If we need to send a caption and voice message was successful, send it as a text message
            if success and caption:
                logger.info(f"Sending caption as text message: {caption[:50]}...")
                text_success = await send_text_message(chat_id, caption)
                if not text_success:
                    logger.warning("Caption was not sent successfully")
                
            return True
    except Exception as e:
        logger.error(f"Error sending voice message: {str(e)}", exc_info=True)
        return False
