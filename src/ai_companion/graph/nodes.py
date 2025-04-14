import os
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig

from ai_companion.graph.state import AICompanionState
from ai_companion.graph.utils.chains import (
    get_character_response_chain,
    get_router_chain,
)
from ai_companion.graph.utils.helpers import (
    get_chat_model,
    get_text_to_image_module,
    get_text_to_speech_module,
)
from ai_companion.modules.memory.long_term.memory_manager import get_memory_manager
from ai_companion.modules.schedules.context_generation import ScheduleContextGenerator
from ai_companion.modules.schedules.reminder import add_reminder
from ai_companion.settings import settings


async def router_node(state: AICompanionState):
    chain = get_router_chain()
    response = await chain.ainvoke({"messages": state["messages"][-settings.ROUTER_MESSAGES_TO_ANALYZE :]})
    return {"workflow": response.response_type}


def context_injection_node(state: AICompanionState):
    schedule_context = ScheduleContextGenerator.get_current_activity()
    if schedule_context != state.get("current_activity", ""):
        apply_activity = True
    else:
        apply_activity = False
    return {"apply_activity": apply_activity, "current_activity": schedule_context}


async def conversation_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    memory_context = state.get("memory_context", "")

    chain = get_character_response_chain(state.get("summary", ""))
    response = await chain.ainvoke(
        {
            "messages": state["messages"],
            "current_activity": current_activity,
            "memory_context": memory_context,
        },
        config,
    )
    return {"messages": AIMessage(content=response)}


async def image_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    memory_context = state.get("memory_context", "")

    chain = get_character_response_chain(state.get("summary", ""))
    text_to_image_module = get_text_to_image_module()

    scenario = await text_to_image_module.create_scenario(state["messages"][-5:])
    os.makedirs("generated_images", exist_ok=True)
    img_path = f"generated_images/image_{str(uuid4())}.png"
    await text_to_image_module.generate_image(scenario.image_prompt, img_path)

    # Inject the image prompt information as an AI message
    scenario_message = HumanMessage(content=f"<image attached by Ava generated from prompt: {scenario.image_prompt}>")
    updated_messages = state["messages"] + [scenario_message]

    response = await chain.ainvoke(
        {
            "messages": updated_messages,
            "current_activity": current_activity,
            "memory_context": memory_context,
        },
        config,
    )

    return {"messages": AIMessage(content=response), "image_path": img_path}


async def audio_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    memory_context = state.get("memory_context", "")

    chain = get_character_response_chain(state.get("summary", ""))
    text_to_speech_module = get_text_to_speech_module()

    response = await chain.ainvoke(
        {
            "messages": state["messages"],
            "current_activity": current_activity,
            "memory_context": memory_context,
        },
        config,
    )
    output_audio = await text_to_speech_module.synthesize(response)

    return {"messages": response, "audio_buffer": output_audio}


async def summarize_conversation_node(state: AICompanionState, config: RunnableConfig = None):
    model = get_chat_model()
    summary = state.get("summary", "")

    if summary:
        summary_message = (
            f"This is summary of the conversation to date between Ava and the user: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = (
            "Create a summary of the conversation above between Ava and the user. "
            "The summary must be a short description of the conversation so far, "
            "but that captures all the relevant information shared between Ava and the user:"
        )

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = await model.ainvoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][: -settings.TOTAL_MESSAGES_AFTER_SUMMARY]]
    return {"summary": response.content, "messages": delete_messages}


async def memory_extraction_node(state: AICompanionState, config: RunnableConfig = None):
    """Extract and store important information from the last message, segregated by chat_id."""
    if not state["messages"]:
        return {}

    memory_manager = get_memory_manager()
    chat_id = str(state.get("chat_id", "global"))
    await memory_manager.extract_and_store_memories(state["messages"][-1], chat_id)
    return {}


def memory_injection_node(state: AICompanionState):
    """Retrieve and inject relevant memories into the character card, segregated by chat_id."""
    memory_manager = get_memory_manager()
    chat_id = str(state.get("chat_id", "global"))

    # Get relevant memories based on recent conversation and chat_id
    recent_context = " ".join([m.content for m in state["messages"][-3:]])
    memories = memory_manager.get_relevant_memories(recent_context, chat_id)

    # Format memories for the character card
    memory_context = memory_manager.format_memories_for_prompt(memories)

    return {"memory_context": memory_context}


import re
from datetime import datetime

import dateparser
import pytz

async def reminder_node(state: AICompanionState, config: RunnableConfig = None):
    """
    Sub-agent node for handling reminders.
    Uses LLM to extract reminder text and time expression, parses with Python, saves to DB, and returns acknowledgement.
    """
    model = get_chat_model()
    chat_id = str(state.get("chat_id", "global"))
    user_message = state["messages"][-1].content

    # Prompt for LLM to extract reminder details (time expression, not ISO datetime)
    prompt = (
        "You are a reminder extraction agent. "
        "Given the following user message, extract the reminder text and the reminder time expression (e.g., '9.00pm', 'tomorrow morning', 'next Friday at 8'). "
        "Do NOT attempt to convert to a datetime. "
        "Respond in JSON format: {\"reminder_text\": ..., \"reminder_time_expression\": ...}.\n\n"
        f"User message: {user_message}"
    )

    response = await model.ainvoke([{"role": "user", "content": prompt}])
    # Try to extract JSON from the response
    import json
    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not match:
        return {"messages": AIMessage(content="Sorry, I couldn't understand the reminder details. Please try again.")}
    try:
        data = json.loads(match.group(0))
        reminder_text = data["reminder_text"]
        reminder_time_expr = data["reminder_time_expression"]
    except Exception:
        return {"messages": AIMessage(content="Sorry, I couldn't parse the reminder details. Please try again with a clear time and message.")}

    # Parse the time expression using dateparser with IST
    ist = pytz.timezone("Asia/Kolkata")
    # Use the timestamp of the user message as the base (if available)
    now_ist = datetime.now(ist)
    reminder_time = dateparser.parse(
        reminder_time_expr,
        settings={
            "TIMEZONE": "Asia/Kolkata",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now_ist,
        },
    )
    if not reminder_time:
        return {"messages": AIMessage(content="Sorry, I couldn't understand the time you mentioned. Please try again with a clear time (e.g., '9pm today', 'tomorrow at 8am').")}

    # Save to DB
    add_reminder(chat_id, reminder_text, reminder_time)

    # Get current IST time at the moment of confirmation
    ist = pytz.timezone("Asia/Kolkata")
    confirmation_time_ist = datetime.now(ist)

    # Format confirmation message
    reminder_time_str = reminder_time.strftime('%d %b, %I:%M%p IST')
    set_time_str = confirmation_time_ist.strftime('%d %b, %I:%M%p IST')
    ack = (
        f"✅ Reminder set for {reminder_time_str} to: {reminder_text}.\n"
        f"🕒 Set at: {set_time_str} (IST)"
    )
    return {"messages": AIMessage(content=ack)}
