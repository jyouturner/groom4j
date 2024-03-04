
def save_response(response, response_file="response.txt"):
        with open(response_file, "a") as f:
            # add a separator to separate the responses
            f.write("=====================================\n")
            f.write(response + "\n")

def load_the_last_response(response_file="response.txt"):
    with open(response_file, "r") as f:
        # read the last response based on the separator
        lines = f.readlines()
        response = ""
        for line in reversed(lines):
            if line.startswith("==="):
                break
            response = line + response
        return response
    
def save_promot(prompt, prompt_file="prompt.txt"):
    with open(prompt_file, "a") as f:
        # add a separator to separate the prompt
        f.write("=====================================\n")
        f.write(prompt + "\n")

def reset_file(file):
    with open(file, "w") as f:
        f.write("")
def reset_prompt_response():
    reset_file("prompt.txt")
    reset_file("response.txt")

import os
use_llm = os.environ.get("USE_LLM")

if use_llm == "openai":
    # use openai
    from llm_openai import query_gpt
    print("Using OpenAI LLM")
elif use_llm == "gemini":
    # use gemini
    from llm_gemini import query_gemini
    print("Using Gemini LLM")
else:
    print("Please set the environment variable USE_LLM to either openai or gemini")
    exit(1)

def query(prompt):
    save_promot(prompt)
    if use_llm == "openai":
        response = query_gpt(prompt)
    elif use_llm == "gemini":
        response = query_gemini(prompt)
    save_response(response)
    return response

