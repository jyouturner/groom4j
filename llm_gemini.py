import base64
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from typing import List

class Gemini:
    def __init__(self, project_id: str, location: str, model_name: str, system_prompt: str) -> None:
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.model = None
        self.system_prompt = system_prompt
        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 1,
            "top_p": 0.95,
        }
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        self._initialize_vertexai()
        self.load_model()

    def initialize_vertexai(self) -> None:
        """Initialize VertexAI with the given project and location."""
        vertexai.init(project=self.project_id, location=self.location)

    def load_model(self) -> None:
        """Load the generative model."""
        self.model = GenerativeModel(self.model_name, system_instruction=self.system_prompt)

    def query(self, messages: List[str]) -> None:
        """Generate content based on the input messages."""
        responses = self.model.generate_content(
            messages,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            stream=True,
        )

        for response in responses:
            print(response.text, end="")

        # return the response to one string
        return "".join(responses)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import os
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GCP_LOCATION")
    model_name = os.getenv("GEMINI_MODEL")
    system_prompt = "You are a helpful assistant"
    gemini = Gemini(project_id, location, model_name, system_prompt)
    gemini.query(['Hello, how are you?'])
