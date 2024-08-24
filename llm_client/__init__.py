# llm_client/__init__.py

from .langfuse_setup import initialize_langfuse
#
# make sure the os environment variables are set before importing the llm classes
# since the initialization of langfuse depends on the os environment variables
#
observe, langfuse_context = initialize_langfuse()

from .llm_openai import OpenAIAssistant
from .llm_google_vertexai import VertexAssistant
from .llm_anthropic import AnthropicAssistant
from .llm_router import LLMInterface, OpenAILLM, VertexAILLM, AnthropicLLM, LLMQueryManager, LLMFactory, ResponseManager