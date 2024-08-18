from langfuse.decorators import observe, langfuse_context

from anthropic import Anthropic
import os
from dotenv import load_dotenv
from typing import List, Dict

class AnthropicAssistant:
    def __init__(self, use_history: bool = True):
        load_dotenv(override=True)
        self.anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        self.system_prompt = None
        self.cached_prompt = None
        self.use_history = use_history
        self.reset_messages()

    def set_system_prompts(self, system_prompt: str, cached_prompt: str = None):
        self.system_prompt = system_prompt
        if cached_prompt is not None:
            if self.is_support_cached_prompt():
                self.cached_prompt = cached_prompt
            else:
                print("Cached prompt is not supported by this assistant. Will append it to the system prompt.")
                self.system_prompt += "\n" + cached_prompt

    def reset_messages(self):
        self.messages = []  # Remove the initial system message here

    def is_support_cached_prompt(self):
        return True

    @observe(as_type="generation", capture_input=False, capture_output=False)
    def query(self, user_prompt: str) -> str:
        if not self.use_history:
            self.reset_messages()

        self.messages.append({"role": "user", "content": user_prompt})
        system_prompt = [
            {
                "type": "text",
                "text": self.system_prompt
            }
        ]
        if self.is_support_cached_prompt() and self.cached_prompt is not None:
            system_prompt.append({
                "type": "text",
                "text": self.cached_prompt,
                "cache_control": {"type": "ephemeral"}
            })
        langfuse_context.update_current_observation(
            input=system_prompt,
        )
        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.0,
            # support for prompt caching
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            #system=self.system_prompt,
            system=system_prompt,
            messages=self.messages
        )
        langfuse_context.update_current_observation(
            input=self.messages,
            model=self.model,
            output=response.content,
            usage={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
        )
        assistant_message = response.content[0].text

        # Add newline characters to the assistant's response
        # assistant_message = assistant_message.replace("\n", "\nassistant: ")

        if self.use_history:
            self.messages.append({"role": "assistant", "content": assistant_message})
        else:
            self.reset_messages()

        return assistant_message

    def get_session_history(self) -> List[Dict[str, str]]:
        return self.messages if self.use_history else []

    def save_session_history(self, filename: str) -> None:
        if self.use_history:
            with open(filename, 'w') as f:
                for message in self.messages:
                    role = "user" if message.get('role') == "user" else "assistant"
                    content = message.get('content')
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
            self.reset_messages()
            # read session history
            messages = self.read_session_history(filename)
            for message in messages:
                self.messages.append({"role": message['role'], "content": message['content']})
        else:
            print("History loading is disabled when use_history is False.")


    def set_use_history(self, use_history: bool):
        self.use_history = use_history
        if not use_history:
            self.reset_messages()

@observe()
def main():
    system_prompt = "You are a helpful AI assistant specialized in Java development."
    
    # Example with history
    assistant_with_history = AnthropicAssistant(system_prompt, use_history=True)
    print("With history:")
    response = assistant_with_history.query("Hello, what is your name? can you explain Java interfaces?")
    print(response[:100])
    response = assistant_with_history.query("How do they differ from abstract classes?")
    print(response[:100])

    # Example without history
    assistant_without_history = AnthropicAssistant(system_prompt, use_history=False)
    print("\nWithout history:")
    response = assistant_without_history.query("Hello, can you explain Java interfaces?")
    print(response[:100])
    response = assistant_without_history.query("How do they differ from abstract classes?")
    print(response[:100])

    # Save the session for later use
    assistant_with_history.save_session_history("java_session_anthropic.txt")

    # Later, you can load the session and continue
    new_assistant = AnthropicAssistant(system_prompt, use_history=True)
    new_assistant.load_session_history("java_session_anthropic.txt")
    print("\nContinuing loaded session:")
    response = new_assistant.query("Given what we discussed about interfaces and abstract classes, when should I use each?")
    print(response[:100])

    # Switching history mode
    print("\nSwitching history mode:")
    assistant_with_history.set_use_history(False)
    response = assistant_with_history.query("What's the difference between public and private methods?")
    print(response[:100])




