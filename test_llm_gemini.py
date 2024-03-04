import datetime
from pyexpat import model
import time
from unittest.mock import MagicMock
from llm_gemini import query_gemini_model

class MockResponse:
    def __init__(self, text):
        self.text = text

def test_query_gemini_model_success():
    # Mock the model.generate_content function
    model.generate_content = MagicMock(return_value=MockResponse(text="Generated content"))

    prompt = "Test prompt"
    result = query_gemini_model(prompt)

    # Assert that the model.generate_content function was called with the correct prompt
    model.generate_content.assert_called_once_with(prompt)

    # Assert that the returned result is the expected text response
    assert result == "Generated content"

def test_query_gemini_model_retry():
    # Mock the model.generate_content function to raise an exception
    model.generate_content = MagicMock(side_effect=Exception("Some error"))

    prompt = "Test prompt"
    retries = 3

    # Set the sleep function to a MagicMock to avoid actual sleep during the test
    time.sleep = MagicMock()

    result = query_gemini_model(prompt, retries=retries)

    # Assert that the model.generate_content function was called the expected number of times
    assert model.generate_content.call_count == retries + 1

    # Assert that the sleep function was called the expected number of times
    assert time.sleep.call_count == retries

    # Assert that the returned result is None, indicating failure after retries
    assert result is None