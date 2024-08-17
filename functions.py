from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles
from typing import Union

def read_files(pf, file_names) -> str:
    additional_reading = ""
    for file_name in file_names:
        file_name = file_name.strip()
        # check whether it is a single file name or a file name with path
        if "/" in file_name:
            # it is a file name with path
            file_path, file_name = os.path.split(file_name)
            # get the file, package must be Java style
            package = file_path.replace("/", ".")
            filename,filesummary, filepath, filecontent = get_file(pf, file_name, package=package)
        else:
            # it is a single file name
            filename,filesummary, filepath, filecontent = get_file(pf, file_name, package=None)
       
        if filename:
            additional_reading += f"<file name=\"{filename}\">\n"
            additional_reading += f"<summary>{filesummary}</summary>\n"
            additional_reading += f"<content>{filecontent}</content></file>\n"
        else:
            additional_reading += f"!!!File {file_name} does not exist! Please ask for the correct file or packages! I am very disappointed!\n"
    return additional_reading


def read_packages(pf, package_names) -> str:
    additional_reading = ""
    for package_name in package_names:
        # clean it
        package_name = package_name.strip()
        packagename, packagenotes, subpackages, filenames = get_package(pf, package_name)
        if packagename:
            additional_reading += f"<package name=\"{packagename}\">\n"
            additional_reading += f"<notes>{packagenotes}</notes>\n"
            additional_reading += f"<sub_packages>{subpackages}</sub_package>\n"
            additional_reading += f"<files>{filenames}</files>\n"
            additional_reading += f"</package>\n"
    return additional_reading

def read_all_packages(pf) -> str:
    additional_reading = ""
    for package in pf.package_notes:
        additional_reading += f"<package name=\"{package}\"><notes>{pf.package_notes[package]}</notes></package>\n"
    return additional_reading

def read_from_human(line) -> str:
    # ask user to enter manually through commmand line
    print("Question: \n", line)
    human_response = input("Answer:\n")
    additional_reading = f"{human_response}"
    return additional_reading

def search_files_with_keyword(root_path, keyword):
    # search for files with the keyword within the project
    # return the list of file names
    print(f"Searching for files with the keyword: {keyword} under {root_path}")
    matching_files = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith(".java") or file.endswith(".json"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    for line in f:
                        if keyword in line:
                            matching_files.append(file)
                            print(f"Found {keyword} in file: {file_path}")
                            break  # Stop reading the file once the keyword is found
    return matching_files

#
# here are the functions to be used in the pipeline.
#

def get_file(pf, file_name, package=None) -> Tuple[str, str, str, str]:
    """
    given a file name, return the file name, summary, path, and content of the file
    """
    file = pf.find_codefile_by_name(file_name, package)
    if file:
        # now let's get the file content, since we have the path
        full_path = os.path.join(pf.root_path, file.path)
        with open(full_path, "r") as f:
            file_content = f.read()
        return file.filename, file.summary, file.path, file_content
    else:
        return None, None, None, None
    
def get_files(pf, file_names) -> Tuple[Tuple[str, str, str, str]]:
    files = []
    for file_name in file_names:
        # clean it
        file_name = file_name.strip()
        filename, summary, path, content = get_file(pf, file_name)
        if filename:
            files.append((filename, summary, path, content))
    return files

def get_package(pf, package_name) -> Tuple[str, str, str, str]:
    """
    given a package name, return the package name, notes, sub-packages, and file-names
    """
    notes = pf.find_notes_of_package(package_name.strip())
    if not notes:
        print(f"Package {package_name} does not exist in our gist files!")
        notes = ""
        
    subpackages, codefiles = pf.find_subpackages_and_codefiles(package_name)
    subpacakgenames = ', '.join(subpackages)
    codefilenames = ', '.join([f.filename for f in codefiles])
    return package_name, notes, subpacakgenames, codefilenames

def get_packages(pf, package_names) -> Tuple[Tuple[str, str, str, str]]:
    packages = []
    for package_name in package_names:
        # clean it
        package_name = package_name.strip()
        package, notes, subpacakgenames, codefilenames = get_package(pf, package_name)
        if package:
            packages.append((package, notes, subpacakgenames, codefilenames))
    return packages
    
def get_static_notes(pf):
    notes_str = read_all_packages(pf)
        
    # if there is api_notes.md file, then read it and append to the last_response
    default_api_notes_file = "api_notes.md"
    api_notes_file = os.path.join(pf.root_path, ProjectFiles.default_gist_foler, default_api_notes_file)
    if os.path.exists(api_notes_file):
        with open(api_notes_file, "r") as f:
            notes_str += f"\n\n{f.read()}"
    return notes_str