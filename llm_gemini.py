import google.generativeai as genai
import os
import datetime
import time

genai.configure(api_key=os.environ.get("GOOGLE_AI_KEY"))
model = genai.GenerativeModel('gemini-1.0-pro')
model_type = 'gemini'

def query_gemini(
    prompt: str,
    retries: int = 10,
) -> str:
  while True and retries > 0:
    try:
      response = model.generate_content(prompt)
      text_response = response.text.replace("**", "")
      return text_response
    except Exception as e:
      print(f'{datetime.datetime.now()}: query_gemini_model: Error: {e}')
      print(f'{datetime.datetime.now()}: query_gemini_model: Retrying after 5 seconds...')
      retries -= 1
      time.sleep(5)