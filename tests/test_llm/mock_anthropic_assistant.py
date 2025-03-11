import unittest.mock

class MockAnthropicAssistant:
    def __init__(self, use_history: bool = True):
        self.use_history = use_history
        self.system_prompt = None
        self.cached_prompt = None
        self.messages = []

    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt

    def query(self, user_prompt: str) -> str:
        if not self.use_history:
            self.reset_messages()
        
        self.messages.append({"role": "user", "content": user_prompt})
        # Simulate a response based on the prompt
        response = f"Mocked response for: {user_prompt}"
        
        if self.use_history:
            self.messages.append({"role": "assistant", "content": response})
        
        return response

    def reset_messages(self):
        self.messages = []

    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self.reset_messages()

    def is_support_cached_prompt(self):
        return True

# Function to patch the real AnthropicAssistant with our mock
def mock_anthropic_assistant():
    return unittest.mock.patch('llm_client.AnthropicAssistant', MockAnthropicAssistant)
