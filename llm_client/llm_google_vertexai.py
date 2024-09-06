from langfuse.decorators import observe, langfuse_context
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
import vertexai.preview.generative_models as generative_models
from typing import List, Dict, Optional
from .config import LLMConfig
class VertexAssistant:
    def __init__(self, project_id: str, location: str,  config: LLMConfig, use_history: bool = True) -> None:
        self.project_id = project_id
        self.location = location
        self.model_name = config.model_name
        self.use_history = use_history
        self.system_prompt = config.system_prompt
        self.cached_prompt = config.cached_prompt
        self.generation_config = generative_models.GenerationConfig(
            max_output_tokens=config.max_tokens,
            temperature=config.temperature,
            top_p=0.95,
        )
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        self._initialize_vertexai()
        self._initialize_model()

    def _initialize_vertexai(self) -> None:
        vertexai.init(project=self.project_id, location=self.location)

    def _initialize_model(self) -> None:
        combined_prompt = self.system_prompt or ""
        if self.cached_prompt:
            combined_prompt += "\n\n" + self.cached_prompt
        self.model = GenerativeModel(self.model_name, system_instruction=combined_prompt)
        self._start_new_session()

    def _start_new_session(self) -> None:
        self.chat = self.model.start_chat(history=[])

    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
        self._initialize_model()

    @observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, message: str) -> str:
        if not self.use_history:
            self._start_new_session()

        try:
            response = self.chat.send_message(
                message,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )
            
            if response is not None and response.text is not None:
                return response.text
            else:
                print("Received None response or empty text")
                return ""
        except Exception as e:
            print(f"Error during query: {e}")
            print(f"Error type: {type(e)}")
            raise e

    def save_session_history(self, filename: str) -> None:
        if self.use_history:
            with open(filename, 'w') as f:
                for message in self.chat.history:
                    f.write(f"###{message.role}###\n{message.parts[0].text}\n###END###\n")
        else:
            print("History saving is disabled when use_history is False.")



    def load_session_history(self, filename: str) -> None:
        if self.use_history:
            # Use the read_session_history function to load the messages
            messages = self.read_session_history(filename)
            
            # Convert the loaded messages to the format expected by Vertex AI
            loaded_history = []
            for message in messages:
                loaded_history.append(generative_models.Content(
                    role=message['role'],
                    parts=[generative_models.Part.from_text(message['content'])]
                ))
            
            # Rebuild the chat session with the loaded history
            self.chat = self.model.start_chat(history=loaded_history)
            
            print(f"Loaded {len(loaded_history)} messages into the chat history.")
        else:
            print("History loading is disabled when use_history is False.")

    def read_session_history(self, filename: str) -> list:
        history = []
        with open(filename, 'r') as f:
            content = f.read()
        
        messages = content.split("###END###")
        for message in messages:
            message = message.strip()
            if message:
                parts = message.split("\n", 1)
                if len(parts) == 2:
                    role = parts[0].strip("###")
                    content = parts[1].strip()
                    history.append({
                        'role': role,
                        'content': content
                    })
        
        return history
    

if __name__ == "__main__":
    import os
    from config_utils import load_config_to_env
    load_config_to_env()

    config = LLMConfig(model_name=os.environ.get("GCP_MODEL_TIER2_NAME"))
    assistant = VertexAssistant(project_id=os.environ.get("GCP_PROJECT_ID"), location=os.environ.get("GCP_LOCATION"), config=config)
    print(assistant.query("Hello, how are you?"))