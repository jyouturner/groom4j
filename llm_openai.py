# @title Using OpenAI GPT model (DO NOT run the next cell if using GPT)
import openai
from datetime import datetime, time
import os

key = os.environ.get("OPENAI_API_KEY")  #@param {type: "string"}
gpt_client = openai.OpenAI(api_key=key)

def query_gpt(
    prompt: str,
    #lm: str = 'gpt-3.5-turbo-1106',
    lm: str = 'gpt-4o',
    temperature: float = 0.0,
    max_tokens: int = 40560,
    seconds_to_reset_tokens: int = 60,
    ) -> str:
  while True:
    try:
      raw_response = gpt_client.chat.completions.with_raw_response.create(
        model=lm,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
          {'role': 'user', 'content': prompt},
        ]
      )
      completion = raw_response.parse()
      return completion.choices[0].message.content
    except openai.RateLimitError as e:
      print(f'{datetime.datetime.now()}: query_gpt_model: RateLimitError {e.message}: {e}')
      time.sleep(seconds_to_reset_tokens)
    except openai.APIError as e:
      print(f'{datetime.datetime.now()}: query_gpt_model: APIError {e.message}: {e}')
      print(f'{datetime.datetime.now()}: query_gpt_model: Retrying after 5 seconds...')
      time.sleep(5)