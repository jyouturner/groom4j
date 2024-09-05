import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from projectfiles import ProjectFiles
import os
from functions import get_file, get_package, read_files

def test_get_package():
    # find the local path to the test_project folder
    root_path = os.path.join(os.path.dirname(__file__), '..')
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    package_name, notes, subpacakgenames, codefilenames = get_package(pf, "com.iky.travel.config")
   
    assert package_name == "com.iky.travel.config"
    assert codefilenames != ""


def test_ask_file():
    # find the local path to the test_project folder
    root_path = os.path.join(os.path.dirname(__file__), '..')
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    filename, summary, path, file_content = get_file(pf, "CityController.java")

    assert filename == "CityController.java"
    assert path!= ""
   

def test_read_files():
    # find the local path to the test_project folder
    root_path = os.path.join(os.path.dirname(__file__), '..')
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path)
    pf.from_project()

    file_names = ["src/main/resources/application.yaml"]
    content = read_files(pf, file_names)
    print(content)
    assert content != ""