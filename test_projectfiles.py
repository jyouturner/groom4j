import pytest
from projectfiles import CodeFile, ProjectFiles
import os
import json 

def test_create():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    print(pf)
    assert pf.root_path == project_path
    assert pf.prefix_list == ["src/main/java"]
    assert pf.suffix_list == [".java"]

def test_get_files_of_folder():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    files = pf.get_files_from_folder(os.path.join(project_path, "src/main/java"))
    # print the files in detail
    for file in files:
        print(file.filename, file.package)
    # find . -name '*.java'|wc -l
    assert len(files) > 0
    assert len(files) == 28

def test_get_files_of_project():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    files = pf.get_files_of_project()
    # print the files in detail
    for file in files:
        print(file.filename, file.package, file.path)
    # find . -name '*.java'|wc -l
    assert len(files) > 0
    assert len(files) == 28

def test_persist_code_files():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    files = pf.get_files_of_project()
    # use temprary file path for testing
    gist_file_path = os.path.join(root_path, "data/travel-service-dev", "test_gist_files.txt")
    pf.persist_code_files(files, gist_file_path)
    # now load the file and check the content
    files2 = pf.load_code_files(gist_file_path= gist_file_path)
    for file in files2:
        print(file.filename, file.package, file.path)
    assert len(files) == len(files2)
    for i in range(len(files)):
        assert files[i].filename == files2[i].filename
        assert files[i].package == files2[i].package
        assert files[i].path == files2[i].path
        assert files[i].summary == files2[i].summary
    # delete the file
    os.remove(gist_file_path)

def test_generate_package_structure():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    files = pf.get_files_of_project()

    packages = pf.generate_package_structure(files)
    # pretty print the dict
    # the key is "com", the value is another dict, with keys including "files" and "sub_packages",
    # and each subpackage is another dict with keys including "files" and "sub_packages" and so on.
    json_object = json.dumps(packages, indent = 4)
    print(json_object)
    assert len(packages) > 0
    assert len(packages) == 1
    assert "com" in packages
    assert "com.iky" in packages["com"]["sub_packages"]
    assert "com.iky.travel" in packages["com"]["sub_packages"]["com.iky"]["sub_packages"]
    assert "com.iky.travel.config" in packages["com"]["sub_packages"]["com.iky"]["sub_packages"]["com.iky.travel"]["sub_packages"]
    assert "com.iky.travel.controller" in packages["com"]["sub_packages"]["com.iky"]["sub_packages"]["com.iky.travel"]["sub_packages"]
    assert len(packages["com"]["files"]) == 0


def test_code_file_json():
    cf = CodeFile("filename", "path", "package")
    json_str = cf.to_json()
    print(json_str)
    cf2 = CodeFile.from_json(json_str)
    assert cf.filename == cf2.filename

def test_packages_json():
    packages = {
        "com": {
            "files": ["filename1"],
            "sub_packages": {
                "com.iky": {
                    "files": ["filename2"],
                    "sub_packages": {
                        }
                    }
                }
            }
    }
    json_str = json.dumps(packages)
    print(json_str)
    packages2 = json.loads(json_str)
    assert len(packages) == len(packages2)
    assert "com" in packages2
    assert "com.iky" in packages2["com"]["sub_packages"]

def test_package_structure_traverse_top_down():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    
    
    print("\n" + "-" * 110 + "\nTop-Down View:")
    pf.package_structure_traverse(packages=None, action_file_func=lambda package, file: print(f"Executing on file: {package} {file}"), action_package_func=lambda package, subpackages, filenames: print(f"Executing on package: {package} Subpackages: {subpackages}, Filenames: {filenames}"), is_bottom_up=False)

def test_package_structure_traverse_bottom_up():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    
    
    print("\n" + "-" * 110 + "\nBottom-Up View:")
    pf.package_structure_traverse(packages=None, 
                                  action_file_func=lambda package, file: print(f"Executing on file: {package} {file}"), 
                                  action_package_func=lambda package, subpackages, filenames: print(f"Executing on package: {package} Subpackages: {subpackages}, Filenames: {filenames}"), 
                                  is_bottom_up=True)


def test_print_tree():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    files = pf.get_files_of_project()
    packages = pf.generate_package_structure(files)
    # print json
    json_object = json.dumps(packages, indent = 4)
    print(json_object)
    from projectfiles import print_tree
    print("-" * 110 + "\nTree:")
    tree = print_tree(packages)
    print(tree)

def test_find_package_node():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    # find the package node
    node = pf.find_package_node("com.iky.travel.config")
    print(node)
    assert node is not None
    assert node["sub_packages"] == {}
    assert len(node["files"]) == 3

def test_find_codefile_by_name():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    # find the codefile by name
    codefile = pf.find_codefile_by_name("TravelController.java")
    print(codefile)
    assert codefile is not None

def test_find_subpackages_and_codefiles():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    # find the subpackages and codefiles
    subpackages, codefiles = pf.find_subpackages_and_codefiles("com.iky.travel.config")
    print(subpackages)
    print(codefiles)
    assert len(subpackages) == 0
    assert len(codefiles) == 3

def test_persist_package_notes():
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()
    # add couple of package notes
    pf.add_package_notes("com.iky.travel.config", "This is the config package")
    pf.add_package_notes("com.iky.travel.controller", "This is the controller package")
    travel_notes = """
- Purpose: The configuration package is responsible for setting up and managing various configuration aspects of the application. It includes classes and methods to load and handle configuration properties, ensuring that the application has the necessary settings to connect to and interact with external services, such as a pricing orchestration service. It also deals with the retrieval and management of a GraphQL schema which is essential for the application's data interaction layer.

- The package contains a primary configuration class, which is responsible for loading configuration properties specific to the pricing orchestration service and fetching the associated GraphQL schema.

- The package utilizes annotations from the Spring Framework to define configuration properties and manage bean lifecycle events, such as the @PostConstruct annotation used in the fetchSchema() method to load the schema after bean initialization.

- Dependencies like Lombok and Apache Commons IO are used to reduce boilerplate code and handle file operations, respectively, while the Java Validation API ensures that configuration properties are correctly populated.

- The package may also include sub-packages, each with its own set of responsibilities and notes, contributing to the overall configuration management of the application.

    """
    pf.add_package_notes("com.iky.travel", travel_notes)
    # persist the package notes
    gist_file_path = os.path.join(root_path, "data/travel-service-dev", "test_gist_packages.txt")
    pf.persist_package_notes(gist_file_path)
    # now load the file and check the content
    package_notes = pf.load_package_notes(gist_file_path)
    print(package_notes)
    assert len(package_notes) > 0
    assert "com.iky.travel.config" in package_notes
    assert "com.iky.travel.controller" in package_notes
    assert "com.iky.travel" in package_notes
    assert pf.find_notes_of_package("com.iky.travel.config") == "This is the config package"
    # delete
    os.remove(gist_file_path)

def test_package_structure_traverse_bottom_up_package_notes():
    from projectfiles import dumb_package_gisting
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    # traverse the package structure bottom up to fill all the notes of packages and files
    def fnFile(package, file):
        print(f"Executing on file: {package} {file}")
    def dumb_package_gisting(package, subpackage_notes, filenotes):
        return f"This is the summary of package {package}"
    def fnPackage(package, subpackages, filenames):
        print(f"Executing on package: {package} Subpackages: {subpackages}, Filenames: {filenames}")
        print(f"Package gisting: {dumb_package_gisting(package, subpackages, filenames)}")
    
    pf.package_structure_traverse(packages=None, 
                                  action_file_func=fnFile, 
                                  action_package_func=fnPackage, 
                                  is_bottom_up=True)

def test_find_package_notes():
    from projectfiles import dumb_package_gisting
    # find the local path to the test_project folder
    root_path = os.path.dirname(os.path.abspath(__file__))
    print("root path", root_path)
    project_path = os.path.join(root_path, "data/travel-service-dev")
    print("project path", project_path)
    pf = ProjectFiles(project_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    pf.from_project()

    # find the package notes
    notes = pf.find_notes_of_package("com.iky.travel.config")
    print(notes)
    assert notes != ""
