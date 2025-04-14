from langfuse.callback import CallbackHandler
from functools import lru_cache

@lru_cache(maxsize=1)
def get_langfuse_handler():
    """
    Returns a singleton Langfuse CallbackHandler for Langchain/LangGraph tracing.
    Configuration is read from environment variables:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    """
    return CallbackHandler()
