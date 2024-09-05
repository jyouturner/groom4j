import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from projectfiles import ProjectFiles, CodeFile

use_llm = "gemini"  # You can change this to test different LLM providers

# Global variable to hold the LLMQueryManager class, which is imported in the setup_env fixture
# this is important because the LLMQueryManager class is not available until langfuse is initialized
# which depends on the config_utils module
LLMQueryManager = None

@pytest.fixture(scope="module", autouse=True)
def setup_env():
    # Load configuration into environment variables
    from config_utils import load_config_to_env
    load_config_to_env(config_path="application.yml")
    global LLMQueryManager
    from llm_client import LLMQueryManager
    

@pytest.fixture
def querymanager(setup_env):
    from llm_interaction import process_llm_response, initiate_llm_query_manager
    from gist_files import system_prompt
    qm = initiate_llm_query_manager(pf=None, system_prompt=system_prompt, reused_prompt_template=None)
    return qm

def test_gist_java_file(querymanager):
    project_root = "./data/travel-service-dev"
    javaCodeFile = CodeFile(filename="TravelController.java", 
                            path="src/main/java/com/iky/travel/controller/travel/TravelController.java",
                            package="com.iky.travel.controller",)
    from gist_files import code_gisting
    summary = code_gisting(querymanager, project_root, javaCodeFile)
    assert summary is not None
    print(summary)

def test_gist_java_file2(querymanager):
    project_root = "./data/travel-service-dev"
    javaCodeFile = CodeFile(filename="TravelServiceImpl.java", 
                            path="src/main/java/com/iky/travel/domain/service/travel/impl/TravelServiceImpl.java",
                            package="com.iky.travel.domain.service.travel.impl")
    from gist_files import code_gisting
    summary = code_gisting(querymanager, project_root, javaCodeFile)
    assert summary is not None
    print(summary)

def test_gist_config_file(querymanager):
    project_root = "./data/travel-service-dev"
    configCodeFile = CodeFile(filename="application.yaml", 
                            path="src/main/resources/application.yaml",
                            package=None)
    from gist_files import code_gisting
    summary = code_gisting(querymanager, project_root, configCodeFile)
    assert summary is not None
    print(summary)