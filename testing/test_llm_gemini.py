import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from dotenv import load_dotenv
import langfuse_setup
from llm_google_vertexai import VertexAssistant
from projectfiles import ProjectFiles
import os

@pytest.fixture(scope="module", autouse=True)
def setup_env():
    load_dotenv(override=True)

@pytest.fixture
def assistant():
    system_prompt = """
    You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

    Begin your analysis with: "Let's investigate the Java project to answer the question: [restate the question]".
    """
    reused_prompt_template = """
    Below is the Java project structure for your reference:
    {project_tree}

    and summaries of the packages in the project:
    {package_notes}
    """
    root_path = "./data/travel-service-dev"
    pf = ProjectFiles(repo_root_path=root_path)
    pf.from_gist_files()
    
    package_notes = ""
    for package in pf.package_notes:
        package_notes += f"<package name=\"{package}\"><notes>{pf.package_notes[package]}</notes></package>\n"
    cached_prompt = reused_prompt_template.format(project_tree=pf.to_tree(), package_notes=package_notes)   
    
    assistant = VertexAssistant(project_id=os.environ.get("GCP_PROJECT_ID"), location=os.environ.get("GCP_LOCATION"), model_name="gemini-1.5-pro", use_history=False)
    assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=cached_prompt)
    print("Assistant setup complete")
    return assistant

def test_java_assistant(assistant):
    response = assistant.query("how does the project query database?")
    assert response is not None
    print(response[:300])

    response = assistant.query("what are the API endpoints available from the project?")
    assert response is not None
    print(response[:300])




if __name__ == "__main__":
    pytest.main()