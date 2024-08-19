import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from dotenv import load_dotenv
import llm_client.langfuse_setup as langfuse_setup
from llm_client import AnthropicAssistant
from projectfiles import ProjectFiles

@pytest.fixture(scope="module", autouse=True)
def setup_env():
    load_dotenv(override=True)


def java_assistant():
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
    
    assistant = AnthropicAssistant(use_history=False)
    assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=cached_prompt)
    print("Assistant setup complete")
    return assistant

def test_java_assistant():
    java_assistant = java_assistant()
    response = java_assistant.query("how does the project query database?")
    assert response is not None
    print(response[:300])

    response = java_assistant.query("what are the API endpoints available from the project?")
    assert response is not None
    print(response[:300])

def test_system_prompt():
    system_prompt = """
    You manage the mapping between key and value as below:
    Mile -> 102
    Jack -> 3
    Tom -> 22

    You will be asked to provide the value for a given key.
    You only need to return the value for the key. No need to return the key or any other information.
    """
    assistant = AnthropicAssistant(use_history=False)
    assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=None)
    assert assistant.system_prompt == system_prompt
    response = assistant.query("What is the value for Mile?")
    print(f"response is {response}")
    assert response is not None

def test_cached_prompt():
    system_prompt = """
    You manage the mapping between key and value.
    You will be asked to provide the value for a given key.
    You only need to return the value for the key. No need to return the key or any other information.
    """

    cached_prompt = """
    Below is the mapping between key and value:
    Mile -> 102
    Jack -> 3
    Tom -> 22
    """
    assistant = AnthropicAssistant(use_history=False)
    assistant.set_system_prompts(system_prompt=system_prompt, cached_prompt=cached_prompt)
    assert assistant.system_prompt == system_prompt
    response = assistant.query("What is the value for Mile?")
    print(f"response is {response}")
    assert response is not None


if __name__ == "__main__":
    pytest.main()