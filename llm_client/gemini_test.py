import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting, FinishReason
import vertexai.preview.generative_models as generative_models

def generate():
    vertexai.init(project="helloworld-384400", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-001",
        system_instruction=[textsi_1]
    )
    responses = model.generate_content(
        [text1],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )
    print("-----------------")
    for response in responses:
        print(response.text, end="")

text1 = """<example>
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

# Suggested improvement: Add more emphasis on format in the system instruction
textsi_1 = """You are an eCommerce product recommendation assistant. Based on the user's preferences, suggest products that they might like. 
IMPORTANT: Always follow the exact format of the examples provided, including the numbering and brief descriptions."""

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.5,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

generate()