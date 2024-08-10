# langfuse setup
import os
from langfuse.decorators import observe
from langfuse.openai import openai
from datetime import datetime
import time
import os
from typing import List, Dict

#else:
#    def with_langtrace_root_span():
#      def decorator(any, func):
#              return func
#      return decorator

class OpenAIAssistant:
    def __init__(self, system_prompt: str, model: str = 'gpt-4', temperature: float = 0.0, max_tokens: int = 2048, use_history: bool = True):
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.use_history = use_history
        self.reset_conversation()

    def reset_conversation(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    @observe()
    def query(self, user_prompt: str) -> str:
        if not self.use_history:
            self.reset_conversation()
        
        self.messages.append({"role": "user", "content": user_prompt})
        
        while True:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=self.messages
                )
                #completion = raw_response.parse()
                assistant_message = completion.choices[0].message.content
                
                if self.use_history:
                    self.messages.append({"role": "assistant", "content": assistant_message})
                else:
                    self.reset_conversation()
                
                print(f"OpenAIAssistant.query returning: {type(assistant_message)}")
                return assistant_message
            
            except openai.RateLimitError as e:
                print(f'{datetime.now()}: query_gpt_model: RateLimitError {e.message}: {e}')
                time.sleep(60)
            except openai.APIError as e:
                print(f'{datetime.now()}: query_gpt_model: APIError {e.message}: {e}')
                print(f'{datetime.now()}: query_gpt_model: Retrying after 5 seconds...')
                time.sleep(5)

    def get_session_history(self) -> List[Dict[str, str]]:
        return self.messages if self.use_history else []

    def save_session_history(self, filename: str) -> None:
        if self.use_history:
            with open(filename, 'w') as f:
                for message in self.messages:
                    #f.write(f"{message['role']}: {message['content']}\n")
                    f.write(f"###{message['role']}###\n{message['content']}\n###END###\n")
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
            self.reset_conversation()
            # read the messages from the file
            messages = self.read_session_history(filename)
            for message in messages:
                self.messages.append({"role": message['role'], "content": message['content']})
        else:
            print("History loading is disabled when use_history is False.")

    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self.reset_conversation()

if __name__ == "__main__":
    
    from dotenv import load_dotenv
    load_dotenv()
    openai.langfuse_auth_check()
    system_prompt = "You are a helpful AI assistant specialized in Java development."
    
    # Example with history
    assistant_with_history = OpenAIAssistant(system_prompt, use_history=True)
    print("With history:")
    response = assistant_with_history.query("Hello, can you explain Java interfaces?")
    print(response[:100])
    response = assistant_with_history.query("How do they differ from abstract classes?")
    print(response[:100])

    # Example without history
    assistant_without_history = OpenAIAssistant(system_prompt, use_history=False)
    print("\nWithout history:")
    response = assistant_without_history.query("Hello, can you explain Java interfaces?")
    print(response[:100])
    response = assistant_without_history.query("How do they differ from abstract classes?")
    print(response[:100])

    # Save the session for later use
    assistant_with_history.save_session_history("java_session_openai.txt")

    # Later, you can load the session and continue
    new_assistant = OpenAIAssistant(system_prompt, use_history=True)
    new_assistant.load_session_history("java_session_openai.txt")
    print("\nContinuing loaded session:")
    response = new_assistant.query("Given what we discussed about interfaces and abstract classes, when should I use each?")
    print(response[:100])

    # Switching history mode
    print("\nSwitching history mode:")
    assistant_with_history.set_use_history(False)
    response = assistant_with_history.query("What's the difference between public and private methods?")
    print(response[:100])