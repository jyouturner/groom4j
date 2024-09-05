from .langfuse_setup import observe, langfuse_context

from anthropic import Anthropic, RateLimitError
import os
from typing import List, Dict
from time import sleep

# Claude 3 Sonnet
SONNET_INPUT_COST = 0.00000300  # $0.003 per 1000 tokens
SONNET_OUTPUT_COST = 0.00001500  # $0.015 per 1000 tokens

class AnthropicAssistant:
    def __init__(self, use_history: bool = True):
        self.anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        self.system_prompt = None
        self.cached_prompt = None
        self.use_history = use_history
        self.reset_messages()
        self.max_retries = 3
        self.base_delay = 20  # 5 seconds

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

    @observe(as_type="generation", name="query", capture_input=False, capture_output=False)
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

        for attempt in range(self.max_retries):
            try:
                response = self.anthropic.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0.0,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
                    system=system_prompt,
                    messages=self.messages
                )
                break  # If successful, break out of the retry loop
            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limit reached. Retrying in {delay} seconds...")
                    sleep(delay)
                else:
                    print("Max retries reached. Please try again later.")
                    raise e

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

        if self.use_history:
            self.messages.append({"role": "assistant", "content": assistant_message})
        else:
            self.reset_messages()
        
        try:
            print(f"\ncost: {self.get_cost()}\n")
        except Exception as e:
            print(e)
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

    def get_cost(self) -> float:
        #usage = langfuse_context.current_observation.get("usage")
        #input_cost = usage.get("input") * SONNET_INPUT_COST
        #output_cost = usage.get("output") * SONNET_OUTPUT_COST
        #return input_cost + output_cost
        return 0.0





