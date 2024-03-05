import datetime
from pyexpat import model
import time
from unittest.mock import MagicMock
from llm_gemini import query_gemini
from dotenv import load_dotenv
load_dotenv(override=True)

def test_llm_gemini():
    response = query_gemini("hello world!")
    print(response)
    assert response is not None
    assert response != ""
    