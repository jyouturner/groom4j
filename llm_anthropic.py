from anthropic import Anthropic
import os
from dotenv import load_dotenv

def query_anthropic(system_prompt, user_prompt):
    anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), 
                          #default_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"}
                          )
    print("Using Anthropic ... interestingly using max_tokens beyond 2048 seems to make the LLM dumb and ask more questions...")
    response = anthropic.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        max_tokens=2048,
        temperature=0.0,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.content[0].text

if __name__ == "__main__":
    load_dotenv(override=True)
    
    system_prompt = "You are a helpful AI assistant."
    user_prompt = "Hello, world!"
    
    response = query_anthropic(system_prompt, user_prompt)
    print(response)
