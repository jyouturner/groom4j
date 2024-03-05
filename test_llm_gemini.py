import os
from llm_gemini import query_gemini
from dotenv import load_dotenv
load_dotenv(override=True)

def test_llm_gemini():
    # skip if env is not set
    if os.environ.get("GOOGLE_API_KEY") is None:
        return
    response = query_gemini("hello world!")
    print(response)
    assert response is not None
    assert response != ""
    