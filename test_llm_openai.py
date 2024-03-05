import pytest
import os
from dotenv import load_dotenv
load_dotenv(override=True)

def test_llm_openai():
    if os.environ.get("OPENAI_API_KEY") is None:
        return
    from llm_openai import query_gpt
    
    response = query_gpt("hello world!")
    print(response)
    assert response is not None
    assert response != ""