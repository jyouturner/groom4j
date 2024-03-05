import pytest

from dotenv import load_dotenv
load_dotenv(override=True)

def test_llm_openai():
    from llm_openai import query_gpt
    
    response = query_gpt("hello world!")
    print(response)
    assert response is not None
    assert response != ""