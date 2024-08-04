import os
import google.generativeai as genai
from typing import List, Dict
from dotenv import load_dotenv

class GenAIAssistant:
    def __init__(self, api_key: str, model_name: str, system_prompt: str, use_history: bool = True) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.chat_session = None
        self.use_history = use_history
        self.system_prompt = system_prompt
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self._initialize_genai()
        self.load_model()

    def _initialize_genai(self) -> None:
        genai.configure(api_key=self.api_key)

    def load_model(self) -> None:
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
        )
        self._start_new_session()

    def _start_new_session(self) -> None:
        self.chat_session = self.model.start_chat(
            history=[
                {"role": "user", "parts": [self.system_prompt]},
                {"role": "model", "parts": ["Understood. I'm ready to assist with Java project analysis and task grooming. How can I help you today?"]}
            ]
        )

    def query(self, message: str) -> str:
        if not self.use_history:
            self._start_new_session()

        response = self.chat_session.send_message(message, stream=True)
        full_response = ""
        for chunk in response:
            #print(chunk.text, end="")
            full_response += chunk.text
        #print()  # New line after response

        if not self.use_history:
            self._start_new_session()

        return full_response

    def get_session_history(self) -> List[Dict[str, str]]:
        return self.chat_session.history if self.use_history else []

    def save_session_history(self, filename: str) -> None:
        if self.use_history:
            with open(filename, 'w') as f:
                for message in self.chat_session.history:
                    role = "user" if message.role == "user" else "model"
                    content = message.parts[0].text if hasattr(message.parts[0], 'text') else str(message.parts[0])
                    f.write(f"###{role}###\n{content}\n###END###\n")
        else:
            print("History saving is disabled when use_history is False.")

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

    def load_session_history(self, filename: str) -> None:
        if self.use_history:
            self._start_new_session()  # Start with a fresh session
            messages = self.read_session_history(filename)
            for message in messages:
                role = message['role']
                content = message['content']
                self.chat_session.history.append({
                        'role': 'model',
                        'parts': [content]
                }) if role == 'model' else self.chat_session.history.append({
                        'role': 'user',
                        'parts': [content]
                })
        else:
            print("History loading is disabled when use_history is False.")

    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self._start_new_session()


def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    model_name = "gemini-pro"
    system_prompt = "You are a helpful AI assistant specialized in Java development."

    # Create an instance of GenAIAssistant
    assistant = GenAIAssistant(api_key, model_name, system_prompt)

    # Test with history
    print("With history:")
    response = assistant.query("Hello, can you explain Java interfaces?")
    print(response[:100])
    response = assistant.query("How do they differ from abstract classes?")
    print(response[:100])

    # Save the session history
    assistant.save_session_history("java_session_genai.txt")

    # Create a new instance without history
    assistant_without_history = GenAIAssistant(api_key, model_name, system_prompt, use_history=False)
    print("\nWithout history:")
    response = assistant_without_history.query("What are the main features of Java?")
    print(response[:100])
    response = assistant_without_history.query("Can you give an example of polymorphism in Java?")
    print(response[:100])

    # Load the previous session and continue
    new_assistant = GenAIAssistant(api_key, model_name, system_prompt)
    new_assistant.load_session_history("java_session_genai.txt")
    print("\nContinuing loaded session:")
    response = new_assistant.query("Given what we discussed about interfaces and abstract classes, when should I use each?")
    print(response[:100])

    # Test switching history mode
    print("\nSwitching history mode:")
    assistant.set_use_history(False)
    response = assistant.query("What's the difference between public and private methods in Java?")
    print(response[:100])

if __name__ == "__main__":
    main()


    