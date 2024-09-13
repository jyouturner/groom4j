import os
from .langfuse_setup import observe, langfuse_context
from openai import OpenAI, RateLimitError, APIError
from datetime import datetime
import time
import os
from typing import List, Dict
from .config import LLMConfig

class OpenAIAssistant:
    def __init__(self, config: LLMConfig, use_history: bool = True):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = config.model_name
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.system_prompt = config.system_prompt
        self.cached_prompt = config.cached_prompt
        self.use_history = use_history
        self.reset_conversation()

    def is_support_cached_prompt(self):
          return False
    
    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        self.cached_prompt = cached_prompt
        if cached_prompt is not None and not self.is_support_cached_prompt():
            print("Cached prompt is not supported by this assistant. Will add it to the system prompt.")
            self.system_prompt += "\n" + cached_prompt
            self.cached_prompt = None
        self.reset_conversation()
                

    def reset_conversation(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
        

    @observe(as_type="generation", capture_input=False, capture_output=False)
    def query(self, user_prompt: str) -> str:
        if not self.use_history:
            self.reset_conversation()
        
        self.messages.append({"role": "user", "content": user_prompt})
        
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=self.messages
                )
                #completion = raw_response.parse()
                assistant_message = response.choices[0].message.content
                langfuse_context.update_current_observation(
                    input=self.messages,
                    model=self.model,
                    output=assistant_message,
                    usage={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens
                    }
                )
                if self.use_history:
                    self.messages.append({"role": "assistant", "content": assistant_message})
                else:
                    self.reset_conversation()
                
                print(f"OpenAIAssistant.query returning: {type(assistant_message)}")
                return assistant_message
            
            except RateLimitError as e:
                print(f'{datetime.now()}: query_gpt_model: RateLimitError {e.message}: {e}')
                # do not retry if 'code': 'insufficient_quota'
                if e.code != 'insufficient_quota':
                    time.sleep(60)
                else:
                    raise e
            except APIError as e:
                print("self.messages:", self.messages)
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
    from config_utils import load_config_to_env
    load_config_to_env()
    config = LLMConfig(api_key=os.environ.get("OPENAI_API_KEY"), model_name=os.environ.get("OPENAI_MODEL_TIER2_NAME"))
    assistant = OpenAIAssistant(config)
    print(assistant.query("Hello, how are you?"))
    print(assistant.query("why?"))