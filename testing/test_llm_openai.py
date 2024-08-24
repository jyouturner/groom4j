import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
# Load configuration into environment variables
from config_utils import load_config_to_env
load_config_to_env(config_path="testing/application_test.yml")
import llm_client.langfuse_setup as langfuse_setup
from llm_client import OpenAIAssistant
from projectfiles import ProjectFiles

# Global variable to hold the AnthropicAssistant class
OpenAIAssistant = None
from mock_openai_assistant import mock_openai_assistant

@pytest.fixture(scope="module", autouse=True)
def setup_env():
    # Load configuration into environment variables
    from config_utils import load_config_to_env
    load_config_to_env(config_path="testing/application_test.yml")
    # Import OpenAIAssistant after loading config, and after langfuse is initialized
    # this is important because the OpenAIAssistant class is not available until langfuse is initialized
    global OpenAIAssistant
    with mock_openai_assistant():
        from llm_client import OpenAIAssistant
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
    
    
    with mock_openai_assistant():
        assistant = OpenAIAssistant(use_history=False)
        assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=cached_prompt)
        print("Assistant setup complete")
        return assistant

def test_java_assistant(assistant):
    response = assistant.query("how does the project query database?")
    assert response is not None
    assert "Mocked OpenAI response for:" in response
    print(response[:300])

    response = assistant.query("what are the API endpoints available from the project?")
    assert response is not None
    assert "Mocked OpenAI response for:" in response
    print(response[:300])


def test_history():
    with mock_openai_assistant():
        system_prompt = "You are a helpful AI assistant specialized in Java development."
        
        # Example with history
        assistant_with_history = OpenAIAssistant(use_history=True)
        assistant_with_history.set_system_prompts(system_prompt=system_prompt, cached_prompt=None)
        print("With history:")
        response = assistant_with_history.query("Hello, can you explain Java interfaces?")
        print(response[:100])
        response = assistant_with_history.query("How do they differ from abstract classes?")
        print(response[:100])

        # Example without history
        assistant_without_history = OpenAIAssistant(use_history=False)
        assistant_without_history.set_system_prompts(system_prompt=system_prompt, cached_prompt=None)
        print("\nWithout history:")
        response = assistant_without_history.query("Hello, can you explain Java interfaces?")
        print(response[:100])
        response = assistant_without_history.query("How do they differ from abstract classes?")
        print(response[:100])

        # Save the session for later use
        assistant_with_history.save_session_history("java_session_openai.txt")

        # Later, you can load the session and continue
        new_assistant = OpenAIAssistant(use_history=True)
        new_assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=None)
        new_assistant.load_session_history("java_session_openai.txt")
        print("\nContinuing loaded session:")
        response = new_assistant.query("Given what we discussed about interfaces and abstract classes, when should I use each?")
        print(response[:100])

        # Switching history mode
        print("\nSwitching history mode:")
        assistant_with_history.set_use_history(False)
        response = assistant_with_history.query("What's the difference between public and private methods?")
        print(response[:100])

        assert "Mocked OpenAI response for:" in response

if __name__ == "__main__":
    pytest.main()