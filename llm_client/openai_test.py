import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

# Initialize the client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate():
    system_instruction = """You are an eCommerce product recommendation assistant. Based on the user's preferences, suggest products that they might like. 
    IMPORTANT: Always follow the exact format of the examples provided, including the numbering, brief descriptions, and XML tags."""

    user_prompt = """<example>
<input>I'm looking for a lightweight laptop with a long battery life for travel.</input>
<output>
1. MacBook Air - Lightweight, 18-hour battery life, sleek design.
2. Dell XPS 13 - Compact, 19-hour battery life, high performance.
3. Lenovo ThinkPad X1 Carbon - Durable, 15-hour battery life, travel-friendly.
</output>
</example>
<example>
<input>I need a smartphone with a great camera and plenty of storage.</input>
<output>
1. iPhone 14 Pro - 48MP camera, 1TB storage, excellent photo quality.
2. Samsung Galaxy S23 Ultra - 200MP camera, 1TB storage, top-notch features.
3. Google Pixel 7 Pro - 50MP camera, 512GB storage, superb night mode.
</output>
</example>

Follow the exact format of the examples above, use the tag <output> to wrap the results.

<input>I am interested in a gaming console with a large game library and online multiplayer capabilities.</input>
"""

    response = client.chat.completions.create(
        model="gpt-4",  # You can change this to gpt-3.5-turbo or other available models
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=300,
        temperature=0.5,
        top_p=0.95,
    )

    print("-----------------")
    print(response.choices[0].message.content)

if __name__ == "__main__":
    generate()