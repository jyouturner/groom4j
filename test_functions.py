from projectfiles import ProjectFiles
import os
from functions import get_file, get_package

def test_get_package():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    result = get_package(pf, "com.iky.travel.config")
    print(result)
    assert result[0] == "com.iky.travel.config"
    assert result[1] != ""
    assert result[2] == ""
    assert result[3] == "MongoConfig.java, RedisConfig.java, WebSecurityConfiguration.java"
    result = get_package(pf, "com.iky.travel.controller")
    print(result)
    assert result[0] == "com.iky.travel.controller"
    assert result[1] != ""
    assert result[2] == "com.iky.travel.controller.city, com.iky.travel.controller.travel"
    assert result[3] == ""

def test_ask_file():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    result = get_file(pf, "CityController.java")
    print(result)
    assert result[0] == "CityController.java"
    assert result[1] != ""
    assert result[2] != ""
    assert result[3] != ""