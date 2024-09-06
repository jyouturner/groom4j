from collections import defaultdict
import os
import json
from abc import ABC, abstractmethod

class CodeFile:
    def __init__(self, filename, path, package):
        self.filename = filename
        self.path = path
        self.package = package
        self.summary = ""
        #self.imports = ""
        #self.functions = ""
        #self.todo_comments = ""
        # a function to gist packages, only used in the package_structure_traverse
        self.package_gisting_func = None

    def set_details(self, summary):
        self.summary = summary
        #self.imports = imports
        #self.functions = functions
        #self.todo_comments = todo_comments

    def set_summary(self, summary):
        self.summary = summary

    def get_summary(self):
        return self.summary

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)
        code_file = CodeFile(data['filename'], data['path'], data['package'])
        code_file.set_details(data.get('summary', ''))

        return code_file

    def __str__(self):
        return f"CodeFile(filename={self.filename}, path={self.path}, package={self.package}, summary={self.summary})"

    def __repr__(self):
        return f"CodeFile(filename={self.filename!r}, path={self.path!r}, package={self.package!r}, summary={self.summary!r})"

def dumb_package_gisting(package, subpackage_notes, filenotes):
    return f"This is the summary of package {package}"

class FilePersistence(ABC):
    @abstractmethod
    def persist_package_notes(self, package_notes, file_path):
        pass

    @abstractmethod
    def load_package_notes(self, file_path):
        pass

    @abstractmethod
    def persist_code_files(self, files, gist_file_path):
        pass

    @abstractmethod
    def load_code_files(self, gist_file_path):
        pass

class DefaultFilePersistence(FilePersistence):
    def __init__(self, separator="|"):
        self.separator = separator

    def persist_package_notes(self, package_notes: dict[str, str], file_path: str) -> str:
        with open(file_path, "w") as f:
            for package, notes in package_notes.items():
                f.write(self.separator)
                f.write(f"Package: {package}\nNotes: {notes}\n\n")
        return file_path

    def load_package_notes(self, file_path) -> dict[str, str]:
        package_notes = defaultdict(str)
        with open(file_path, "r") as f:
            content = f.read()
            package_blocks = content.split(self.separator)
            for block in package_blocks:
                if block.strip():
                    lines = block.split("\n")
                    current_package = None
                    notes = []
                    for line in lines:
                        if line.startswith("Package:"):
                            current_package = line.split(":", 1)[1].strip()
                        elif line.startswith("Notes:"):
                            notes.append(line.split(":", 1)[1].strip())
                        elif line.strip():
                            notes.append(line.strip())
                    if current_package:
                        package_notes[current_package] = "\n".join(notes)
        return package_notes

    def persist_code_files(self, files: list[CodeFile], gist_file_path: str) -> str:
        with open(gist_file_path, "w") as f:
            for file in files:
                f.write(self.separator)
                f.write(f"Filename: {file.filename}\n")
                f.write(f"Path: {file.path}\n")
                f.write(f"Package: {file.package}\n")
                f.write(f"Summary: {file.summary}\n")
                f.write("\n")
        return gist_file_path

    def load_code_files(self, gist_file_path: str) -> list[CodeFile]:
        files = []
        with open(gist_file_path, "r") as f:
            content = f.read()
            file_blocks = content.split(self.separator)
            for block in file_blocks:
                if block.strip():
                    lines = block.split("\n")
                    file_data = {}
                    current_key = None
                    for line in lines:
                        if ": " in line and not line.startswith(" "):
                            key, value = line.split(": ", 1)
                            file_data[key] = value
                            current_key = key
                        elif current_key:
                            file_data[current_key] += "\n" + line

                    if 'Filename' in file_data and 'Path' in file_data and 'Package' in file_data:
                        code_file = CodeFile(file_data['Filename'], file_data['Path'], file_data['Package'])
                        code_file.set_details(file_data.get('Summary', '').strip())
                        files.append(code_file)
        return files

class ProjectFiles:
    default_codefile_gist_file = "code_files.txt"
    default_package_notes_file = "package_notes.txt"
    default_gist_foler = ".gist"
    default_seporator = "|"

    def __init__(self, repo_root_path, prefix_list = None, suffix_list = None, resource_suffix_list=None, persistence=None):
        self.root_path = repo_root_path
        # default prefix list should be ["src/main/java", "src/main/resources", "src/test/java", "src/test/resources"]
        if prefix_list is None:
            prefix_list = ["src/main/java", "src/main/resources", "src/test/java", "src/test/resources"]
        
        self.prefix_list = prefix_list
        # default suffix list should be [".java", ".xml", ".yml", ".yaml", ".properties", ".sql", ".json"]
        if suffix_list is None:
            suffix_list = [".java", ".xml", ".yml", ".yaml", ".properties", ".sql", ".json"]
        self.suffix_list = suffix_list
        #FIXME, the suffix list and resource_suffix_list are conflicting, need to fix it
        self.resource_suffix_list = resource_suffix_list or ['.properties', '.yaml', ".yml", ".json", '.xml']
        self.package_notes = defaultdict(str)
        self.files = []
        self.resource_files = []
        self.packages = {}
        self.gist_file_path = None
        self.package_gisting_func = None
        self.persistence = persistence or DefaultFilePersistence(self.default_seporator)

    def from_files(self, files):
        self.files = files
        self.packages = self.generate_package_structure(files)

    def from_folder(self, folder_path):
        self.files = self.get_files_from_folder(folder_path)
        self.packages = self.generate_package_structure(self.files)

    def from_project(self, gist_file_path=None):
        java_files = self.get_files_of_project()
        print(f"Java files found: {len(java_files)}")
        resource_files = self.get_resource_files()
        print(f"Resource files found: {len(resource_files)}")
        
        # if gist_file_path is not set, then use the default path
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)

        self.gist_file_path = gist_file_path

        if os.path.exists(gist_file_path):
            
            print(f"Loading existing gist files from {gist_file_path}")
            existing_files = self.load_code_files(gist_file_path)
            # Update summaries for existing files
            for existing_file in existing_files:
                for new_file in java_files + resource_files:
                    if existing_file.filename == new_file.filename and existing_file.path == new_file.path:
                        new_file.summary = existing_file.summary
        else:
            print(f"{gist_file_path} does not exist, so we will not load existing gist files")

        
        self.files = java_files
        self.resource_files = resource_files
        self.packages = self.generate_package_structure(self.files)
    
        
        gist_folder_path = os.path.dirname(gist_file_path)
        if os.path.exists(os.path.join(gist_folder_path, self.default_package_notes_file)):
            print(f"Loading package notes from {self.default_package_notes_file}")
            self.package_notes = self.load_package_notes()
        else:
            print(f"No package notes file {self.default_package_notes_file} found at {gist_folder_path}")

    def from_gist_files(self, gist_file_path=None):
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)
        if os.path.exists(gist_file_path):
            print(f"Loading code gist files from {gist_file_path}")
            all_files = self.load_code_files(gist_file_path)
            self.files = [f for f in all_files if f.package != "resources"]
            self.resource_files = [f for f in all_files if f.package == "resources"]
            print(f"After loading gist: Java files: {len(self.files)}, Resource files: {len(self.resource_files)}")
            self.gist_file_path = gist_file_path
            self.packages = self.generate_package_structure(self.files)
            gist_folder_path = os.path.dirname(gist_file_path)
            if os.path.exists(os.path.join(gist_folder_path, self.default_package_notes_file)):
                print(f"Loading package notes from {self.default_package_notes_file}")
                self.package_notes = self.load_package_notes()
        else:
            print(f"No existing gist file found at {gist_file_path}")

    def get_files_of_project(self):
        all_files = []
        for prefix in self.prefix_list:
            if os.path.exists(os.path.join(self.root_path, prefix)):
                all_files.extend(self.get_files_from_folder(os.path.join(self.root_path, prefix)))
        return all_files

    def get_resource_files(self):
        resource_files = []
        for prefix in self.prefix_list:
            if prefix.endswith('resources'):
                resource_path = os.path.join(self.root_path, prefix)
                print(f"Searching for resource files in: {resource_path}")
                for root, _, filenames in os.walk(resource_path):
                    for filename in filenames:
                        if filename.endswith(tuple(self.resource_suffix_list)):
                            file_full_path = os.path.join(root, filename)
                            file_relative_path = os.path.relpath(file_full_path, self.root_path)
                            resource_files.append(CodeFile(filename, file_relative_path, "resources"))
                            print(f"Found resource file: {filename}")
        print(f"Total resource files found: {len(resource_files)}")
        return resource_files

    def get_files_from_folder(self, folder_path):
        files = []
        for root, dirs, filenames in os.walk(folder_path):
            for filename in filenames:
                if filename.endswith(tuple(self.suffix_list)):
                    file_full_path = os.path.join(root, filename)
                    package = file_full_path[len(folder_path) + 1: -len(filename) - 1].replace("/", ".")
                    file_relative_path = file_full_path[len(self.root_path) + 1:]
                    files.append(CodeFile(filename, file_relative_path, package))
        return files

    def generate_package_structure(self, files: list[CodeFile]) -> dict[str, dict[str, list[str]]]:
        packages = {}
        for file in files:
            parts = file.package.split('.')
            current = packages
            for i, part in enumerate(parts):
                package_path = '.'.join(parts[:i + 1])
                if package_path not in current:
                    current[package_path] = {"files": [], "sub_packages": {}}
                if i == len(parts) - 1:
                    current[package_path]["files"].append(file.filename)
                current = current[package_path]["sub_packages"]
        return packages

    def check_code_file_exists(self, package: str, fileName: str) -> CodeFile:
        file = self.find_codefile_by_name(fileName, package)
        if not file or not file.summary:
            raise Exception(f"expect file {fileName} have summary by now!")

    def gist_package(self, package: str, subpackages: dict[str, dict[str, list[str]]], filenames: list[str]):
        # check to make sure the function is set
        if self.package_gisting_func is None:
            raise ValueError("package_gisting_func is not set!")
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
        
        notes = self.package_gisting_func(package, subpackage_notes, filenotes)
        self.add_package_notes(package, notes)

    def package_structure_traverse(self, packages=None, action_file_func=check_code_file_exists, action_package_func=gist_package, is_bottom_up=False):
        if packages is None:
            self.packages = self.generate_package_structure(self.files)
            packages = self.packages
        for package, value in sorted(packages.items(), reverse=is_bottom_up):
            sub_packages = value["sub_packages"]
            codefileNames = value["files"]

            if is_bottom_up:
                self.package_structure_traverse(sub_packages, action_file_func, action_package_func, is_bottom_up)

            if action_package_func:
                action_package_func(package, sub_packages, codefileNames)

            for fileName in (reversed(codefileNames) if is_bottom_up else codefileNames):
                if action_file_func:
                    action_file_func(package, fileName)

            if not is_bottom_up:
                self.package_structure_traverse(sub_packages, action_file_func, action_package_func, is_bottom_up)


    def find_codefile_by_name(self, file_name, package=None):
        if self.files is None:
            raise ValueError("Files are not loaded!")
        for file in self.files + self.resource_files:
            if file.filename == file_name and (package is None or file.package == package):
                return file
        return None

    def find_package_node(self, package: str, packages: dict[str, dict[str, list[str]]] = None) -> dict[str, dict[str, list[str]]]:
        if packages is None:
            packages = self.packages
        parts = package.split('.')
        current_structure = packages
        for i in range(len(parts)):
            packagePath = ".".join(parts[:i+1])
            if packagePath in current_structure.keys():
                if i == len(parts) - 1:
                    return current_structure[packagePath]
                else:
                    if "sub_packages" in current_structure[packagePath]:
                        current_structure = current_structure[packagePath]["sub_packages"]
                    else:
                        return None
            else:
                return None
        return current_structure

    def find_subpackages_and_codefiles(self, package: str, packages: dict[str, dict[str, list[str]]] = None) -> tuple[dict[str, dict[str, list[str]]], list[CodeFile]]:
        if packages is None:
            packages = self.packages
        node = self.find_package_node(package)
        code_files = []
        if node:
            sub_packages, file_names = node['sub_packages'], node['files']
            for file_name in file_names:
                for file in self.files:
                    if file.filename == file_name and file.package == package:
                        code_files.append(file)
            return sub_packages, code_files
        else:
            return None, None

    def add_package_notes(self, package: str, notes: str):
        self.package_notes[package] = notes

    def find_notes_of_package(self, package: str) -> str:
        if self.package_notes is None:
            raise ValueError("Package notes is not loaded!")
        return self.package_notes.get(package, None)

    def persist_package_notes(self, file_path: str = None) -> str:
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_package_notes_file)
        gist_folder_path = os.path.dirname(file_path)
        if not os.path.exists(gist_folder_path):
            os.makedirs(gist_folder_path)
        return self.persistence.persist_package_notes(self.package_notes, file_path)

    def load_package_notes(self, file_path: str = None) -> dict[str, str]:
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_package_notes_file)
        print(f"Loading package notes from {file_path}")
        return self.persistence.load_package_notes(file_path)

    def persist_code_files(self, files: list[CodeFile] = None, gist_file_path: str = None) -> str:
        if files is None:
            files = self.files + self.resource_files
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)
        gist_folder_path = os.path.dirname(gist_file_path)
        if not os.path.exists(gist_folder_path):
            os.makedirs(gist_folder_path)
        return self.persistence.persist_code_files(files, gist_file_path)

    def load_code_files(self, gist_file_path: str = None) -> list[CodeFile]:
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)
        return self.persistence.load_code_files(gist_file_path)

    def get_file_notes(self) -> str:
        file_notes = ""
        for file in self.files:
            file_notes += f"File: {file.filename} : {file.summary}\n\n"
        return file_notes
    
    def to_tree(self):
        return print_tree(self.packages)

def print_tree(packages, prefix='', is_last=True):
    result = ""
    for i, (package, contents) in enumerate(packages.items()):
        is_last_item = i == len(packages) - 1
        
        # Determine the appropriate prefix for this level
        if is_last:
            current_prefix = prefix + "└── "
            next_prefix = prefix + "    "
        else:
            current_prefix = prefix + "├── "
            next_prefix = prefix + "│   "

        result += f"{current_prefix}{package}/\n"

        if 'files' in contents and contents['files']:
            for j, file in enumerate(contents['files']):
                is_last_file = j == len(contents['files']) - 1 and 'sub_packages' not in contents
                file_prefix = next_prefix + ("└── " if is_last_file else "├── ")
                result += f"{file_prefix}{file}\n"

        if 'sub_packages' in contents:
            result += print_tree(contents['sub_packages'], next_prefix, is_last_item)

    return result



if __name__ == "__main__":
    pf = ProjectFiles(repo_root_path="data/travel-service-dev")
    pf.from_project()
    tree = print(pf.to_tree())
    print(tree)
