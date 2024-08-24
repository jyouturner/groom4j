import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from mock_llm_router import mock_llm_query_manager, mock_llm_factory
from projectfiles import ProjectFiles

use_llm = "gemini"  # You can change this to test different LLM providers

# Global variable to hold the LLMQueryManager class, which is imported in the setup_env fixture
# this is important because the LLMQueryManager class is not available until langfuse is initialized
# which depends on the config_utils module
LLMQueryManager = None

@pytest.fixture(scope="module", autouse=True)
def setup_env():
    # Load configuration into environment variables
    from config_utils import load_config_to_env
    load_config_to_env(config_path="testing/application_test.yml")
    global LLMQueryManager
    with mock_llm_query_manager(), mock_llm_factory():
        from llm_client import LLMQueryManager
        yield
    


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
    
    with mock_llm_query_manager(), mock_llm_factory():
        assistant = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    

    print(f"{use_llm} assistant setup complete")
    return assistant

def test_java_assistant(assistant):
    response = assistant.query("how does the project query database?")
    assert response is not None
    assert "Mocked response for: how does the project query database?" in response
    print(response[:300])

    response = assistant.query("what are the API endpoints available from the project?")
    assert response is not None
    assert "Mocked response for" in response
    print(response[:300])

@pytest.mark.parametrize("use_llm", ["openai", "gemini", "anthropic"])
def test_different_llm_providers(use_llm):
    with mock_llm_query_manager(), mock_llm_factory():
        assistant = LLMQueryManager(use_llm=use_llm, system_prompt="Test prompt")
        response = assistant.query("Test query")
        assert response is not None
        assert f"Mocked response for: Test query" in response
        print(f"{use_llm} response: {response[:100]}")

if __name__ == "__main__":
    pytest.main()