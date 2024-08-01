import os
from typing import Callable, Optional
from abc import ABC, abstractmethod

# Langtrace setup
if os.environ.get("LANGTRACE_API_KEY") and os.environ.get("LANGTRACE_API_HOST"):
    from langtrace_python_sdk import langtrace, with_langtrace_root_span
    langtrace.init(
        api_key=os.environ.get("LANGTRACE_API_KEY"),
        api_host=os.environ.get("LANGTRACE_API_HOST")
    )
else:
    def with_langtrace_root_span():
        def decorator(func):
            return func
        return decorator

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
    def query(self, system_prompt: str, user_prompt: str) -> str:
        pass

class OpenAILLM(LLMInterface):
    def query(self, system_prompt: str, user_prompt: str) -> str:
        from llm_openai import query_gpt
        return query_gpt(system_prompt, user_prompt)

class GeminiLLM(LLMInterface):
    def __init__(self):
        from llm_gemini import Gemini
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_LOCATION")
        model_name = os.getenv("GEMINI_MODEL")
        self.gemini = Gemini(project_id, location, model_name, "")

    def query(self, system_prompt: str, user_prompt: str) -> str:
        self.gemini.system_prompt = system_prompt
        return self.gemini.query([user_prompt])

class AnthropicLLM(LLMInterface):
    def query(self, system_prompt: str, user_prompt: str) -> str:
        from llm_anthropic import query_anthropic
        return query_anthropic(system_prompt=system_prompt, user_prompt=user_prompt)

class LLMFactory:
    @staticmethod
    def get_llm() -> LLMInterface:
        use_llm = os.environ.get("USE_LLM", "").lower()
        if use_llm == "openai":
            return OpenAILLM()
        elif use_llm == "gemini":
            return GeminiLLM()
        elif use_llm == "anthropic":
            return AnthropicLLM()
        else:
            raise ValueError("Please set the environment variable USE_LLM to either openai, gemini, or anthropic")

class LLMQueryManager:
    def __init__(self):
        self.llm = LLMFactory.get_llm()
        self.response_manager = ResponseManager()

    @with_langtrace_root_span()
    def query(self, system_prompt: str, user_prompt: str) -> str:
        response = self.llm.query(system_prompt, user_prompt)
        self.response_manager.save_response(response)
        return response

# Usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    query_manager = LLMQueryManager()
    system_prompt = "You are a helpful assistant."
    user_prompt = "What's the weather like today?"
    response = query_manager.query(system_prompt, user_prompt)
    print(response)