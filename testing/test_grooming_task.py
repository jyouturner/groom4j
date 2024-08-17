import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch
from projectfiles import ProjectFiles
# Import the function to be tested
from grooming_task import read_files, read_packages
import os

def test_read_files():
    # Create a mock object
    # find the local path to the test_project folder
    root_path = os.path.join(os.path.dirname(__file__), '..')
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    result = read_files(pf, ["TravelBeApplication.java", "MongoConfig.java"])
    # Check the result is not empty
    assert result != ""
    # Check the result contains "TravelBeApplication.java" and "MongoConfig.java"
    assert "TravelBeApplication.java" in result
    assert "MongoConfig.java" in result

def test_read_packages():
    # find the local path to the test_project folder
    root_path = os.path.join(os.path.dirname(__file__), '..')
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java", "src/test/java"], suffix_list=[".java"], resource_suffix_list=[".properties"])
    pf.from_project()

    print(pf.packages)

    result = read_packages(pf, ["com.iky.travel.config"])
    print(result)
    # Check the result is not empty
    assert result != ""
    # Check the result contains "com.iky.travel.config"
    assert "com.iky.travel.config" in result


    