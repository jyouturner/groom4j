# config of the LLM including API key, model name, etc.
class LLMConfig:
    def __init__(self, api_key: str = None, model_name: str = None, temperature: float = 0.0, max_tokens: int = 2048, system_prompt: str = "You are an AI assistant", cached_prompt: str = None):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
