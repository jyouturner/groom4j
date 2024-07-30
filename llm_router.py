
# only set up langtrace when the environment variable is set
import os
if os.environ.get("LANGTRACE_API_KEY") and os.environ.get("LANGTRACE_API_HOST"):
    from langtrace_python_sdk import langtrace, with_langtrace_root_span
    langtrace.init(api_key=os.environ.get("LANGTRACE_API_KEY"),
    api_host=os.environ.get("LANGTRACE_API_HOST")),

# the response file serves as a memory for the conversation
default_respose_file = "response.txt"

def save_response(response, response_file=default_respose_file):
        with open(response_file, "a") as f:
            # add a separator to separate the responses
            f.write("=====================================\n")
            f.write(response + "\n")

def load_the_last_response(response_file=default_respose_file):
    with open(response_file, "r") as f:
        # read the last response based on the separator
        lines = f.readlines()
        response = ""
        for line in reversed(lines):
            if line.startswith("==="):
                break
            response = line + response
        return response

def reset_file(file):
    with open(file, "w") as f:
        f.write("")

def reset_prompt_response():
    reset_file(default_respose_file)

import os
use_llm = os.environ.get("USE_LLM")
print(f"Using LLM: {use_llm}")
if use_llm == "openai":
    # use openai
    from llm_openai import query_gpt
    print("Using OpenAI")
elif use_llm == "gemini":
    # use gemini
    from llm_gemini import query_gemini
    print("Using Gemini")
elif use_llm == "anthropic":
    # use anthropic
    from llm_anthropic import query_anthropic
    print("Using Anthropic")
else:
    print("Please set the environment variable USE_LLM to either openai or gemini or anthropic")
    exit(1)
    
@with_langtrace_root_span()
def query(prompt):

    if use_llm == "openai":
        response = query_gpt(prompt)
    elif use_llm == "gemini":
        response = query_gemini(prompt)
    elif use_llm == "anthropic":
        response = query_anthropic(system_promot="You are an world class software architect.", user_prompt=prompt)
    else:
        print("Please set the environment variable USE_LLM to either openai or gemini or anthropic")
        exit(1)
    # save the response to a file for next round of conversation
    save_response(response)
    return response

