# Description: This file contains the class ProjectFiles, which is used to manage the files in a project, and the package structure of the project.
# This is the main file to manage the files and packages in the project, including the following functionalities:
# - scan the files from the project
# - manage the code gist files
# - manage the package notes
# - functions on the package structure
# 

from collections import defaultdict
import os
import json

import json

class CodeFile:
    def __init__(self, filename, path, package):
        self.filename = filename
        self.path = path
        self.package = package
        self.summary = ""
        

    def set_summary(self, summary):
        self.summary = summary

    def get_summary(self):
        return self.summary

    def to_json(self):
        # Serialize the object to JSON, using a lambda to convert non-serializable objects.
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    @staticmethod
    def from_json(json_str):
        # Deserialize the JSON string to a CodeFile object.
        data = json.loads(json_str)
        code_file = CodeFile(data['filename'], data['path'], data['package'])
        code_file.set_summary(data.get('summary', ''))
        return code_file

    def __str__(self):
        # Return a string representation of the object.
        return f"CodeFile(filename={self.filename}, path={self.path}, package={self.package}, summary={self.summary})"

    def __repr__(self):
        # Return a Python expression that could be used to recreate the object.
        return f"CodeFile(filename={self.filename!r}, path={self.path!r}, package={self.package!r}, summary={self.summary!r})"

def dumb_package_gisting(package, subpackage_notes, filenotes):
        return f"This is the summary of package {package}"
    
class ProjectFiles:
    
    # define const value
    default_codefile_gist_file = "code_files.txt"
    default_package_notes_file = "package_notes.txt"

    def __init__(self, root_path, prefix_list, suffix_list):
        self.root_path = root_path
        self.prefix_list = prefix_list
        self.suffix_list = suffix_list
        # self.files = self.get_files_of_project(root_path, suffix_list)
        # dict to store the package notes
        self.package_notes = defaultdict(str)
        self.files = []
        self.packages = {}
        #
        self.gist_file_path = None

    def from_files(self, files):
        self.files = files
        self.packages = self.generate_package_structure(files)

    def from_folder(self, folder_path):
        self.files = self.get_files_from_folder(folder_path)
        self.packages = self.generate_package_structure(self.files)

    def from_project(self, gist_file_path = None):
        """
        Load the files from the project and create the package structure. Alos load the package notes and file summary if the gist file exists.
        """
        self.files = self.get_files_of_project()
        self.packages = self.generate_package_structure(self.files)
        self.from_gist_files(gist_file_path)

   
    def from_gist_files(self, gist_file_path=None):
        """
        Load the file and package info from the gist files.
        this function is recommended to use after gisting, as it will load everything if the files exist
        """
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_codefile_gist_file)
        if os.path.exists(gist_file_path):
            print(f"Loading code gist files from {gist_file_path}")
            self.files = self.load_code_files(gist_file_path)
            self.gist_file_path = gist_file_path
            self.packages = self.generate_package_structure(self.files)
            # load the package notes if the file exists
            if os.path.exists(os.path.join(self.root_path, self.default_package_notes_file)):
                print(f"Loading package notes from {self.default_package_notes_file}")
                self.package_notes = self.load_package_notes()
    
    # get all the files in the project
    def get_files_of_project(self) -> list[CodeFile]:
        # for each of the prefix_list, scan the files and match the suffix_list
        all_files = []
        for prefix in self.prefix_list:
            if os.path.exists(os.path.join(self.root_path, prefix)):
                all_files.extend(self.get_files_from_folder(os.path.join(self.root_path, prefix)))
        return all_files

    # get all the files in the folder and return a list of CodeFile
    def get_files_from_folder(self, folder_path):
        files = []
        for root, dirs, filenames in os.walk(folder_path):
            for filename in filenames:
                # if the file name ends with anyone of the suffix list, then it is a code file
                if filename.endswith(tuple(self.suffix_list)):
                    file_path = os.path.join(root, filename)
                    # file_name is WebSecurityConfiguration.java
                    # file_path is .com.iky.travel.config.WebSecurityConfiguration.java
                    # package is com.iky.travel.config
                    package = file_path[len(folder_path) + 1: -len(filename) - 1].replace("/", ".")
                    files.append(CodeFile(filename, file_path, package))
        return files

    def generate_package_structure(self, files):
        packages = {}
        for file in files:
            # assume the java package is in the format of com.company.project
            parts = file.package.split('.')
            current = packages

            # Traverse or create the package path in the structure
            for i, part in enumerate(parts):
                package_path = '.'.join(parts[:i + 1])
                if package_path not in current:
                    current[package_path] = {"files": [], "sub_packages": {}}
                if i == len(parts) - 1:
                    current[package_path]["files"].append(file.filename)
                current = current[package_path]["sub_packages"]

        return packages

    def execute_on_file(self, package, fileName):
        file = self.find_codefile_by_name(fileName, package)
        if not file or not file.summary:
            raise Exception(f"expect file {fileName} have summary by now!")

    def execute_on_package(self, package, subpackages, filenames):
        #print(f"\n\nExecuting function on package: {package}")
        # first create the notes of the sub-packages, for each subpackage, we find the notes, and concatenate them all together with the subpackage name
        subpackage_notes = ""
        for subpackage, value in subpackages.items():
            notes = self.find_notes_of_package(subpackage)
            if not notes:
                raise Exception(f"expect subpackage {subpackage} have notes!")
            subpackage_notes += f"Sub package: {subpackage} : {notes}\n\n"
        filenotes = ""
        for filename in filenames:
            file = self.find_codefile_by_name(filename, package)
            if not file:
                raise Exception(f"expect file {filename} exists!")
            if not file.summary:
                raise Exception(f"expect file {filename} have summary!")
            filenotes += f"File: {file.filename} : {file.summary}\n\n"
        # then call the query_model function to get the notes of the package
        notes = self.package_gisting(package, subpackage_notes, filenotes)
        # store the notes in the package_notes dict
        self.add_package_notes(package, notes)

    
    
    def package_structure_traverse(self, packages=None, action_file=execute_on_file, action_package=execute_on_package, is_bottom_up=False):
        """
        traverse the package structure and execute the action on the files and packages
        :param packages: the package dict, like {"com": {"files": ["file1", "file2"], "sub_packages": {"iky": ...}}}
        :param action_file: the function to execute on the file, one argument is the file name
        :param action_package: the function to execute on the package, 3 arugments, package name, subpackages, and file names
        :param is_bottom_up: whether to traverse the tree bottom-up
        """
        if packages is None:
            # if package is not specified, then we regenerate the package structure from the files
            self.packages = self.generate_package_structure(self.files)
            packages = self.packages
        for package, value in sorted(packages.items(), reverse=is_bottom_up):
            sub_packages = value["sub_packages"]
            codefileNames = value["files"]

            # Recursive call for sub-packages first if bottom-up
            if is_bottom_up:
                self.package_structure_traverse(sub_packages, action_file, action_package, is_bottom_up)

            # Action and print for the package
            if action_package:
                action_package(package, sub_packages, codefileNames)

            # Action and print for files
            for fileName in (reversed(codefileNames) if is_bottom_up else codefileNames):
                if action_file:
                    action_file(package, fileName)

            # Recursive call for sub-packages last if top-down
            if not is_bottom_up:
                self.package_structure_traverse(sub_packages, action_file, action_package, is_bottom_up)

    def to_tree(self):
        return print_tree(self.packages)
    
    def find_codefile_by_name(self, file_name, package=None):
        """
        find the file object by name and package. If package is not given, then find the first file with the name
        """
        if self.files is None:
            raise ValueError("Files are not loaded!")
        for file in self.files:
            if file.filename == file_name and (package is None or file.package == package):
                return file
        return None
    
    def find_package_node1(self, package_path, packages=None):
        """
        Find a specific package node within the nested package structure and return its sub-packages and files.

        :param packages: The root dictionary representing the package structure.
        :param package_path: The dot-separated package path string, e.g., "com.acmi.project".
        :return: A dictionary with 'files' and 'sub_packages' of the found package, or None if not found.
        """
        if packages is None:
            packages = self.packages
        parts = package_path.split('.')
        current_node = packages

        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # If it's the last part, we look for the package itself
                if part in current_node:
                    # Return the current package's 'files' and 'sub_packages'
                    return {
                        'files': current_node[part].get('files', []),
                        'sub_packages': current_node[part].get('sub_packages', {})
                    }
            else:  # If it's not the last part, navigate to the next level
                if part in current_node and 'sub_packages' in current_node[part]:
                    current_node = current_node[part]['sub_packages']
                else:
                    # If the path does not exist, return None
                    return None


    def find_package_node(self, package, packages=None):
        """
        Find and return the package node for a given fully qualified package name.
        
        :param package_structure: The root dictionary of the package structure.
        :param package_name: The full package name to find.
        :return: The node of the found package, or None if not found.
        """
        if packages is None:
            packages = self.packages
        # Split the package name into its components
        parts = package.split('.')
        
        # Initialize the current part of the structure to search in
        current_structure = packages
        for i in range(len(parts)):
            # parts are com, iky, travel, etc.
            # we need to create a text version of package path, will be com, com.iky, com.iky.travel, etc.
            packagePath = ".".join(parts[:i+1])
            if packagePath in current_structure.keys():
                # matching so far, are we done yet?
                if i == len(parts) - 1:
                    # if this is the last part, then we are done
                    return current_structure[packagePath]
                else:
                    # if not, then we need to go to the next level, but check first
                    if "sub_packages" in current_structure[packagePath]:
                        current_structure = current_structure[packagePath]["sub_packages"]
                    else:
                        # if the packagePath does not exist, then the package is not found
                        return None
            else:
                # if the packagePath does not exist, then the package is not found
                return None
        
        return current_structure

    def find_subpackages_and_codefiles(self, package, packages=None):
        if packages is None:
            packages = self.packages
        node = self.find_package_node(package)
        code_files = []
        if node:
            sub_packages, file_names = node['sub_packages'], node['files']
            # need to find the codefiles based on the file_names
            for file_name in file_names:
                for file in self.files:
                    if file.filename == file_name and file.package == package:
                        code_files.append(file)
            return sub_packages, code_files
        else:
            return None, None
        
    def add_package_notes(self, package, notes):
        self.package_notes[package] = notes

    def find_notes_of_package(self, package):
        if self.package_notes is None:
            raise ValueError("Package notes is not loaded!")
        return self.package_notes.get(package, None)
    
    # function to persist the package notes
    def persist_package_notes(self, file_path=None) -> str:
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_package_notes_file)
        with open(file_path, "w") as f:
            for package, notes in self.package_notes.items():
                f.write(f"Package: {package}\nNotes: {notes}\n\n")
        return file_path
    
    # funciton to load the package notes from persistence
    def load_package_notes(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_package_notes_file)
        # the package notes file format is as below
        # each package starts with "Package:", with name, the from the next line are "Notes:" and notes lines, which can be one or multiple lines
        # for each package, read until the end of the file or another package.
        package_notes = defaultdict(str)
        print(f"Loading package notes from {file_path}")
        with open(file_path, "r") as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("Package:"):
                    package = lines[i].split(":")[1].strip()
                    notes = ""
                    i += 1
                    # read until the end of the file or another package
                    while i < len(lines) and not lines[i].startswith("Package:"):
                        notes += lines[i]
                        i += 1
                    package_notes[package] = notes
                else:
                    i += 1
        return package_notes

    
    # functions to persist and load the list of CodeFile in a file
    def persist_code_files(self, files=None, gist_file_path=None) -> str:
        if files is None:
            files = self.files
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_codefile_gist_file)
        with open(gist_file_path, "w") as f:
            for file in files:
                f.write(f"Filename: {file.filename}\nPath: {file.path}\nPackage: {file.package}\nSummary: {file.summary}\n\n")
        return gist_file_path

    def load_code_files(self, gist_file_path=None):
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_codefile_gist_file)
        # the file format follow below example
        # Filename: ...java
        # Path: /Users/...
        # Package: com....
        # Summary: - Purpose: Represents a Java class for anonymous complex type
        # - Main functionality: ...
        #
        # we start with "Filename", read line by line until the empty line, then create a CodeFile instance
        files = []
        with open(gist_file_path, "r") as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("Filename:"):
                    filename = lines[i].split(":")[1].strip()
                    path = lines[i+1].split(":")[1].strip()
                    package = lines[i+2].split(":")[1].strip()
                    # summary could be one or multiple lines, read until end of the file or next file
                    # summary line starts with "Summary:"
                    summary = ""
                    i += 3
                    while i < len(lines) and not lines[i].startswith("Filename:"):
                        # first line remove the "Summary:"
                        if lines[i].startswith("Summary:"):
                            summary += lines[i].split(":")[1].strip()
                        else:
                            summary += lines[i]
                        i += 1
                    files.append(CodeFile(filename, path, package))
                    files[-1].set_summary(summary.strip())
                else:
                    i += 1
        return files
    

def print_tree(pacakges, prefix='') -> str:
    # output a big string
    result = ""
    for package, contents in pacakges.items():
        # Print the current package name
        result += f"{prefix}{package}/\n"
        if 'files' in contents and contents['files']:
            for file in contents['files']:
                # Print files in the current package
                result += f"{prefix}    {file}\n"
        if 'sub_packages' in contents:  # Corrected from 'sub-packages' to 'sub_packages'
            # Recurse into sub-packages
            result += print_tree(contents['sub_packages'], prefix=prefix + '    ')
    return result
