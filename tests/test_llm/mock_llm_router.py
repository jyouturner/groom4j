import unittest.mock

class MockLLMInterface:
    def __init__(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt

    def query(self, user_prompt: str) -> str:
        return f"Mocked response for: {user_prompt}"

class MockOpenAILLM(MockLLMInterface):
    pass

class MockVertexAILLM(MockLLMInterface):
    pass

class MockAnthropicLLM(MockLLMInterface):
    pass

class MockLLMFactory:
    @staticmethod
    def get_llm(use_llm: str, system_prompt: str, cached_prompt: str = None) -> MockLLMInterface:
        if use_llm == "openai":
            return MockOpenAILLM(system_prompt, cached_prompt)
        elif use_llm == "gemini":
            return MockVertexAILLM(system_prompt, cached_prompt)
        elif use_llm == "anthropic":
            return MockAnthropicLLM(system_prompt, cached_prompt)
        else:
            raise ValueError("Invalid LLM type")

class MockLLMQueryManager:
    def __init__(self, use_llm: str, system_prompt: str = None, cached_prompt: str = None):
        self.llm = MockLLMFactory.get_llm(use_llm, system_prompt, cached_prompt)

    def query(self, user_prompt: str) -> str:
        return self.llm.query(user_prompt)

def mock_llm_query_manager():
    return unittest.mock.patch('llm_client.LLMQueryManager', MockLLMQueryManager)

def mock_llm_factory():
    return unittest.mock.patch('llm_client.LLMFactory', MockLLMFactory)