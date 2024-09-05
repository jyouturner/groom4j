import os
from typing import Callable, Optional
from abc import ABC, abstractmethod
# set up tracing, use relative import to avoid import errors since they are in the same path
#from .langfuse_setup import observe, langfuse_context


class LLMInterface(ABC):
    @abstractmethod
    def query(self, user_prompt: str) -> str:
        pass


class OpenAILLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_client.llm_openai import OpenAIAssistant
        assistant_without_history = OpenAIAssistant(model=os.environ.get("OPENAI_MODEL"), use_history=False)
        assistant_without_history.set_system_prompts(system_prompt = system_prompt, cached_prompt=cached_prompt)
        self.assistant = assistant_without_history

    #@observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        response = self.assistant.query(user_prompt)
        while callable(response):
            response = response()
        
        return response

    
class VertexAILLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_client.llm_google_vertexai import VertexAssistant
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_LOCATION")
        model_name = os.getenv("GCP_MODEL")
        self.assistant = VertexAssistant(
            project_id, 
            location, 
            model_name, 
            system_prompt=system_prompt, 
            cached_prompt=cached_prompt, 
            use_history=False
        )

    #@observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        return self.assistant.query(user_prompt)

class AnthropicLLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_client.llm_anthropic import AnthropicAssistant
        self.assistant = AnthropicAssistant(use_history=False)
        self.assistant.set_system_prompts(system_prompt = system_prompt, cached_prompt=cached_prompt)

    #@observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        return self.assistant.query(user_prompt)

class LLMFactory: 
    
    @staticmethod
    def get_llm(use_llm: str = "openai", system_prompt: str = "You are a helpful assistant", cached_prompt: str = None) -> LLMInterface:
        if use_llm == "openai":
            return OpenAILLM(system_prompt = system_prompt, cached_prompt = cached_prompt)
        elif use_llm == "gemini":
            return VertexAILLM(system_prompt = system_prompt, cached_prompt = cached_prompt)
        elif use_llm == "anthropic":
            return AnthropicLLM(system_prompt = system_prompt, cached_prompt = cached_prompt)
        else:
            raise ValueError("Please set the environment variable USE_LLM to either openai, gemini, or anthropic")

class LLMQueryManager:
    def __init__(self, use_llm: str, system_prompt: str = None, cached_prompt: str = None):
        if not use_llm:
            raise ValueError("Please set the environment variable USE_LLM to either openai, gemini, or anthropic")
        
        self.llm = LLMFactory.get_llm(use_llm= use_llm, system_prompt = system_prompt, cached_prompt = cached_prompt)

    def support_cached_prompt(self) -> bool:
        # only turn on prompt caching with Anthropic
        return self.llm.is_support_cached_prompt()

    #@observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        response = self.llm.query(user_prompt)
        return response
    
    def get_total_tokens(self) -> int:
        # should we track or leverage the observability like langfuse_context?
        return 0

# Usage
if __name__ == "__main__":
    # Load configuration into environment variables
    from config_utils import load_config_to_env
    load_config_to_env()
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "What's the weather like today?"
   
   # now we test each of the LLMs, including OpenAI, Google GenAI, Google VertexAI, and Anthropic

    assistant = LLMQueryManager(use_llm='openai', system_prompt = system_prompt)
    response = assistant.query(user_prompt)
    print(response[:100])

    assistant = LLMQueryManager(use_llm='gemini', system_prompt = system_prompt)
    response = assistant.query(user_prompt)
    print(response[:100])

    assistant = LLMQueryManager(use_llm='anthropic', system_prompt = system_prompt)
    response = assistant.query(user_prompt)
    print(response[:100])

    #langfuse_context.flush()

