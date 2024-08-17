import os
from typing import Callable, Optional
from abc import ABC, abstractmethod
# set up tracing
from langfuse_setup import observe, langfuse_context


DEFAULT_RESPONSE_FILE = "response.txt"

class ResponseManager:
    @staticmethod
    def save_response(response: str, response_file: str = DEFAULT_RESPONSE_FILE) -> None:
        with open(response_file, "a") as f:
            f.write("=====================================\n")
            f.write(response + "\n")

    @staticmethod
    def load_last_response(response_file: str = DEFAULT_RESPONSE_FILE) -> str:
        try:
            with open(response_file, "r") as f:
                responses = f.read().split("=====================================\n")
                return responses[-1].strip() if responses else ""
        except FileNotFoundError:
            return ""

    @staticmethod
    def reset_file(file: str) -> None:
        open(file, "w").close()

    @classmethod
    def reset_prompt_response(cls) -> None:
        cls.reset_file(DEFAULT_RESPONSE_FILE)

class LLMInterface(ABC):
    @abstractmethod
    def query(self, user_prompt: str) -> str:
        pass


class OpenAILLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_openai import OpenAIAssistant
        assistant_without_history = OpenAIAssistant(model=os.environ.get("OPENAI_MODEL"), use_history=False)
        assistant_without_history.set_system_prompts(system_prompt = system_prompt, cached_prompt=cached_prompt)
        self.assistant = assistant_without_history
    @observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        response = self.assistant.query(user_prompt)
        print(f"OpenAILLM self.assistant.query returning: {type(response)}")
        while callable(response):
            response = response()
        print(f"OpenAILLM.query returning: {type(response)}")
        
        return response

    
class VertexAILLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_google_vertexai import VertexAssistant
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_LOCATION")
        model_name = os.getenv("GEMINI_MODEL")
        self.assistant = VertexAssistant(
            project_id, 
            location, 
            model_name, 
            system_prompt=system_prompt, 
            cached_prompt=cached_prompt, 
            use_history=False
        )

    @observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        return self.assistant.query(user_prompt)

class AnthropicLLM(LLMInterface):
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        from llm_anthropic import AnthropicAssistant
        self.assistant = AnthropicAssistant(use_history=False)
        self.assistant.set_system_prompts(system_prompt = system_prompt, cached_prompt=cached_prompt)

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
        self.response_manager = ResponseManager()

    def support_cached_prompt(self, use_llm) -> bool:
        # only turn on prompt caching with Anthropic
        return self.llm.is_support_cached_prompt()

    @observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, user_prompt: str) -> str:
        response = self.llm.query(user_prompt)
        print(f"LLMQueryManager.query received: {type(response)}")
        self.response_manager.save_response(response)
        return response

# Usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
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

    langfuse_context.flush()

