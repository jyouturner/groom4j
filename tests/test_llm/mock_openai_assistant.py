import unittest.mock

class MockOpenAIAssistant:
    def __init__(self, model: str = 'gpt-4o', temperature: float = 0.0, max_tokens: int = 2048, use_history: bool = True):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_history = use_history
        self.system_prompt = None
        self.cached_prompt = None
        self.messages = []

    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
        self.reset_conversation()

    def reset_conversation(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def query(self, user_prompt: str) -> str:
        if not self.use_history:
            self.reset_conversation()
        
        self.messages.append({"role": "user", "content": user_prompt})
        response = f"Mocked OpenAI response for: {user_prompt}"
        
        if self.use_history:
            self.messages.append({"role": "assistant", "content": response})
        
        return response

    def save_session_history(self, filename: str) -> None:
        pass  # Mock implementation

    def load_session_history(self, filename: str) -> None:
        pass  # Mock implementation

    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self.reset_conversation()

def mock_openai_assistant():
    return unittest.mock.patch('llm_client.OpenAIAssistant', MockOpenAIAssistant)
