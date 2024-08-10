from langfuse.decorators import observe, langfuse_context
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
import vertexai.preview.generative_models as generative_models
from typing import List, Dict, Optional

class VertexAssistant:
    def __init__(self, project_id: str, location: str, model_name: str, system_prompt: str, use_history: bool = True) -> None:
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.use_history = use_history
        self.generation_config = generative_models.GenerationConfig(
            max_output_tokens=8192,
            temperature=1,
            top_p=0.95,
        )
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        self._initialize_vertexai()
        self.load_model()

    def _initialize_vertexai(self) -> None:
        vertexai.init(project=self.project_id, location=self.location)

    def load_model(self) -> None:
        self.model = GenerativeModel(self.model_name)
        self._start_new_session()

    def _start_new_session(self) -> None:
        self.chat = self.model.start_chat(history=[])
        if self.system_prompt:
            self.chat.send_message(self.system_prompt)

    def get_session_history(self) -> List[Dict[str, str]]:
        if self.use_history:
            return [{"role": msg.role, "content": msg.parts[0].text} for msg in self.chat.history]
        else:
            return []

    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self._start_new_session()
    @observe(as_type="generation", capture_input=True, capture_output=True)
    def query(self, message: str) -> str:
        if not self.use_history:
            self._start_new_session()

        try:
            response = self.chat.send_message(
                message,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=True,
            )
            full_response = ""
            for chunk in response:
                #print(chunk.text, end="", flush=True)
                full_response += chunk.text
            #print()  # New line after response
            return full_response
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Chat history:")
            for msg in self.chat.history:
                print(f"{msg.role}: {msg.parts[0].text[:50]}...")  # Print first 50 chars of each message
            print("Resetting chat session...")
            self._start_new_session()
            return f"Error: {str(e)}"

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
    from dotenv import load_dotenv
    load_dotenv()
    import os

    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GCP_LOCATION")
    model_name = os.getenv("GEMINI_MODEL")
    system_prompt = "You are a helpful assistant specialized in Java development."

    gemini = VertexAssistant(project_id, location, model_name, system_prompt)
    
    # Example usage
    print("With history:")
    print(gemini.query("Hello, can you explain Java interfaces?"))
    print(gemini.query("How do they differ from abstract classes?"))

    # Save the session for later use
    gemini.save_session_history("java_session_vertex.txt")

    # Example without history
    gemini_without_history = VertexAssistant(project_id, location, model_name, system_prompt, use_history=False)
    print("\nWithout history:")
    print(gemini_without_history.query("What are the main features of Java?"))
    print(gemini_without_history.query("Can you give an example of polymorphism in Java?"))

    # Later, you can load the session and continue
    new_gemini = VertexAssistant(project_id, location, model_name, system_prompt)
    new_gemini.load_session_history("java_session_vertex.txt")
    print("\nContinuing loaded session:")
    print(new_gemini.query("Given what we discussed about interfaces and abstract classes, when should I use each?"))

    # Test switching history mode
    print("\nSwitching history mode:")
    gemini.set_use_history(False)
    print(gemini.query("What's the difference between public and private methods in Java?"))
    langfuse_context.flush()