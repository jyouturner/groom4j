from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles
from typing import Union, List, Tuple
import time
def read_files(pf, file_names) -> Tuple[str, List[str], List[str]]:
    additional_reading = ""
    files_found = []
    files_not_found = []
    for file_name in file_names:
        file_name = file_name.strip()
        print("need to read file:", file_name)
        # check whether it is a single file name or a file name with path
        if "/" in file_name:
            # if it starts with '/', that is unexpected, since we don't read from absolute path
            if file_name.startswith("/"):
                print(f"!!!File {file_name} does not meet expectations we are looking for relative path!")
                additional_reading += f"\nFile name=\"{file_name}\"\n"
                additional_reading += f"Expected file name with relative path, starting with src/main/java or src/test/java, but got {file_name}\n"
                continue
            # it is a file name with path, it could be src/main/java/com/iky/travel/config/TravelBeApplication.java ...
            file_path, file_name = os.path.split(file_name)
            # let's find the "src/main/java" in the file_path, then we can get the package name
            if "src/main/java" in file_path:
                file_path = file_path.replace("src/main/java/", "")
            elif "src/test/java" in file_path:
                file_path = file_path.replace("src/test/java/", "")
            elif "src/main/resources" in file_path:
                # FIXME: we need to handle the resources folder differently, since it is not a java file
                print("resources file:", file_path)
                file_path = file_path.replace("src/main/resources", "")
            else:
                print(f"!!!File {file_name} does not meet expectations we are looking for src/main/java or src/test/java in the path!")
                additional_reading += f"\nFile name=\"{file_name}\"\n"
                additional_reading += f"Expected file name with relative path, starting with src/main/java or src/test/java, but got {file_name}\n"
                continue
            package = file_path.replace("/", ".")
            # if package is empty, then use None
            if package == "":
                package = None
            filename,filesummary, filepath, filecontent = get_file(pf, file_name, package=package)
        else:
            # it is a single file name, then we look up in the code_files to find the path and summary, then read the file
            filename,filesummary, filepath, filecontent = get_file(pf, file_name, package=None)
       
        if filename:
            additional_reading += f"\nFile name=\"{filename}\" path=\"{filepath}\"\n"
            additional_reading += f"Summary:{filesummary}\n"
            additional_reading += f"Source Code:\n{filecontent}\n"
            files_found.append(filename)
        else:
            print(f"!!!File {file_name} does not exist!")
            additional_reading += f"\nFile name=\"{file_name}\"\n"
            additional_reading += f"!!!File {file_name} does not exist!\n"
            files_not_found.append(file_name)
    return additional_reading, files_found, files_not_found


def read_packages(pf, package_names) -> Tuple[str, List[str], List[str]]:
    additional_reading = ""
    packages_found = []
    packages_not_found = []
    for package_name in package_names:
        # clean it
        package_name = package_name.strip()
        packagename, packagenotes, subpackages, filenames = get_package(pf, package_name)
        if packagename:
            additional_reading += f"\npackage name=\"{packagename}\"\n"
            additional_reading += f"Summary:{packagenotes}</notes>\n"
            additional_reading += f"sub_packages:{subpackages}\n"
            additional_reading += f"Files:{filenames}\n"
            additional_reading += f"\n"
            packages_found.append(packagename)
        else:
            packages_not_found.append(package_name)
    return additional_reading, packages_found, packages_not_found

def read_all_packages(pf) -> str:
    additional_reading = ""
    for package in pf.package_notes:
        additional_reading += f"\npackage name=\"{package}\"\nSummary:{pf.package_notes[package]}\n"
    return additional_reading

def read_from_human(line) -> str:
    # ask user to enter manually through commmand line
    print("Question: \n", line)
    human_response = input("Answer:\n")
    additional_reading = f"{human_response}"
    return additional_reading

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

def efficient_file_search(root_path: str, keyword: str, max_files: int = 1000, max_file_size: int = 1_000_000, file_extensions: List[str] = None) -> List[str]:
    """
    Search for a keyword in files within a directory, returning relative paths of matching files.
    
    :param root_path: The root directory to start the search from.
    :param keyword: The keyword to search for.
    :param max_files: Maximum number of files to search (default 1000).
    :param max_file_size: Maximum file size in bytes to consider (default 1MB).
    :param file_extensions: List of file extensions to search (e.g., ['.java', '.json']). If None, search all files.
    :return: List of relative file paths containing the keyword.
    """
    matching_files = []
    files_searched = 0
    
    def search_file(file_path: str, rel_path: str) -> Tuple[str, bool]:
        try:
            if os.path.getsize(file_path) > max_file_size:
                return rel_path, False
            
            with open(file_path, 'r', errors='ignore') as file:
                if keyword.lower() in file.read().lower():
                    print(f"Found {keyword} in file: {rel_path}")
                    return rel_path, True
        except Exception as e:
            print(f"Error reading {rel_path}: {e}")
        
        return rel_path, False

    def is_valid_file(file_path: str) -> bool:
        if file_extensions:
            return any(file_path.lower().endswith(ext.lower()) for ext in file_extensions)
        return True

    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count() or 1)) as executor:
        futures = []
        for root, _, files in os.walk(root_path):
            if files_searched >= max_files:
                break
            for file in files:
                if files_searched >= max_files:
                    break
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_path)
                if is_valid_file(file_path):
                    futures.append(executor.submit(search_file, file_path, rel_path))
                    files_searched += 1

        for future in as_completed(futures):
            rel_path, found = future.result()
            if found:
                matching_files.append(rel_path)

    return matching_files


#
# here are the functions to be used in the pipeline.
#

def get_file(pf, file_name, package=None) -> Tuple[str, str, str, str]:
    """
    given a file name, return the file name, summary, path, and content of the file
    """
    print("attempting to find file:", file_name, "package:", package)
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
    

def process_file_request(lines):
    file_request = ""
    file_names = []
    in_file_request = False
    
    for line in lines:
        line = line.strip()
        if "[I need content of files:" in line or "[I need access files:" in line:
            in_file_request = True
            file_request += line
            if "]" in line:  # Handle single-line case
                break
        elif in_file_request and "]" in line:
            file_request += line
            break
        elif in_file_request:
            file_request += line
        else:
            break  # Stop if we're not in a file request and haven't found one
    
    if file_request:
        # Extract content between square brackets
        bracket_content = re.search(r'\[(I need (?:content of|access) files:.*?)\]', file_request, re.DOTALL)
        if bracket_content:
            content = bracket_content.group(1)
            # Extract file names
            pattern = r'<file>(.*?)</file>'
            file_names = re.findall(pattern, content)
    
    return file_names
def get_static_notes(pf):
    notes_str = read_all_packages(pf)
        
    # if there is api_notes.md file, then read it and append to the last_response
    default_api_notes_file = "api_notes.md"
    api_notes_file = os.path.join(pf.root_path, ProjectFiles.default_gist_foler, default_api_notes_file)
    if os.path.exists(api_notes_file):
        with open(api_notes_file, "r") as f:
            notes_str += f"\n\n{f.read()}"
    return notes_str

def save_response_to_markdown(question: str, response: str, path: str) -> str:
    """
    Save the response to a markdown file.

    Args:
        question (str): The question string used to generate the filename.
        response (str): The response content to be saved in the file.
        path (str): The directory where the file will be saved.

    Returns:
        str: The path to the saved markdown file.
    """
    # if path does not exist, create it
    if not os.path.exists(path):
        os.makedirs(path)
    result_file = re.sub(r"[^a-zA-Z0-9]", "_", question.lower())  + ".md"
    result_file = os.path.join(path, result_file)
    with open(result_file, "w") as f:
        f.write(response)
    return result_file