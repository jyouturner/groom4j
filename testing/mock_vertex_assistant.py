import unittest.mock

class MockVertexAssistant:
    def __init__(self, project_id: str, location: str, model_name: str, system_prompt: str = None, cached_prompt: str = None, use_history: bool = True):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.use_history = use_history
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
        self.messages = []

    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
        self._start_new_session()

    def _start_new_session(self):
        self.messages = []

    def query(self, message: str) -> str:
        if not self.use_history:
            self._start_new_session()
        
        self.messages.append({"role": "user", "content": message})
        response = f"Mocked Vertex AI response for: {message}"
        
        if self.use_history:
            self.messages.append({"role": "assistant", "content": response})
        
        return response

    def save_session_history(self, filename: str) -> None:
        pass  # Mock implementation

    def load_session_history(self, filename: str) -> None:
        pass  # Mock implementation



def mock_vertex_assistant():
    return unittest.mock.patch('llm_client.VertexAssistant', MockVertexAssistant)