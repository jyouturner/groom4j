import pytest
from unittest.mock import patch
from projectfiles import ProjectFiles
# Import the function to be tested
from ask import read_files, read_packages
import os

def test_read_files():
    # Create a mock object
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
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
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    result = read_packages(pf, ["com.iky.travel.config"])

    # Check the result is not empty
    assert result != ""
    assert result.startswith("Info about package: com.iky.travel.config")