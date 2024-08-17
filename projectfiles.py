from collections import defaultdict
import os
import json

class CodeFile:
    def __init__(self, filename, path, package):
        self.filename = filename
        self.path = path
        self.package = package
        self.summary = ""
        self.imports = ""
        self.functions = ""
        self.todo_comments = ""
        # a function to gist packages, only used in the package_structure_traverse
        self.package_gisting_func = None

    def set_details(self, summary, imports, functions, todo_comments):
        self.summary = summary
        self.imports = imports
        self.functions = functions
        self.todo_comments = todo_comments

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
        code_file.set_details(data.get('summary', ''), data.get('imports', ''), data.get('functions', ''),data.get('todo_comments', ''))

        return code_file

    def __str__(self):
        return f"CodeFile(filename={self.filename}, path={self.path}, package={self.package}, summary={self.summary})"

    def __repr__(self):
        return f"CodeFile(filename={self.filename!r}, path={self.path!r}, package={self.package!r}, summary={self.summary!r})"

def dumb_package_gisting(package, subpackage_notes, filenotes):
    return f"This is the summary of package {package}"

class ProjectFiles:
    default_codefile_gist_file = "code_files.txt"
    default_package_notes_file = "package_notes.txt"
    default_gist_foler = ".gist"

    def __init__(self, repo_root_path, prefix_list = None, suffix_list = None, resource_suffix_list=None):
        self.root_path = repo_root_path
        self.prefix_list = prefix_list
        self.suffix_list = suffix_list
        self.resource_suffix_list = resource_suffix_list or ['.properties', '.yaml', ".yml", ".json", '.xml']
        self.package_notes = defaultdict(str)
        self.files = []
        self.resource_files = []
        self.packages = {}
        self.gist_file_path = None

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
        
        if gist_file_path and os.path.exists(gist_file_path):
            print(f"Loading existing gist files from {gist_file_path}")
            existing_files = self.load_code_files(gist_file_path)
            # Update summaries for existing files
            for existing_file in existing_files:
                for new_file in java_files + resource_files:
                    if existing_file.filename == new_file.filename and existing_file.path == new_file.path:
                        new_file.summary = existing_file.summary
        
        self.files = java_files
        self.resource_files = resource_files
        self.packages = self.generate_package_structure(self.files)
    
        if gist_file_path:
            self.gist_file_path = gist_file_path
            gist_folder_path = os.path.dirname(gist_file_path)
            if os.path.exists(os.path.join(gist_folder_path, self.default_package_notes_file)):
                print(f"Loading package notes from {self.default_package_notes_file}")
                self.package_notes = self.load_package_notes()

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

    def generate_package_structure(self, files):
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

    def check_code_file_exists(self, package, fileName):
        file = self.find_codefile_by_name(fileName, package)
        if not file or not file.summary:
            raise Exception(f"expect file {fileName} have summary by now!")

    def gist_package(self, package, subpackages, filenames):
        # check to make sure the function is set
        if not self.package_gisting_func:
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

    def to_tree(self):
        return print_tree(self.packages)

    def find_codefile_by_name(self, file_name, package=None):
        if self.files is None:
            raise ValueError("Files are not loaded!")
        for file in self.files + self.resource_files:
            if file.filename == file_name and (package is None or file.package == package):
                return file
        return None

    def find_package_node(self, package, packages=None):
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

    def find_subpackages_and_codefiles(self, package, packages=None):
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

    def add_package_notes(self, package, notes):
        self.package_notes[package] = notes

    def find_notes_of_package(self, package):
        if self.package_notes is None:
            raise ValueError("Package notes is not loaded!")
        return self.package_notes.get(package, None)

    def persist_package_notes(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_package_notes_file)
        gist_folder_path = os.path.dirname(file_path)
        if not os.path.exists(gist_folder_path):
            os.makedirs(gist_folder_path)
        with open(file_path, "w") as f:
            for package, notes in self.package_notes.items():
                f.write(f"Package: {package}\nNotes: {notes}\n\n")
        return file_path

    def load_package_notes(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_package_notes_file)
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
                    while i < len(lines) and not lines[i].startswith("Package:"):
                        notes += lines[i]
                        i += 1
                    package_notes[package] = notes
                else:
                    i += 1
        return package_notes

    def persist_code_files(self, files=None, gist_file_path=None):
        if files is None:
            files = self.files + self.resource_files
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)
        gist_folder_path = os.path.dirname(gist_file_path)
        if not os.path.exists(gist_folder_path):
            os.makedirs(gist_folder_path)
        with open(gist_file_path, "w") as f:
            for file in files:
                f.write(f"Filename: {file.filename}\n")
                f.write(f"Path: {file.path}\n")
                f.write(f"Package: {file.package}\n")
                f.write(f"Summary: {file.summary}\n")
                f.write(f"Imports: {file.imports}\n")
                f.write(f"Functions: {file.functions}\n")
                f.write(f"TODO Comments: {file.todo_comments}\n")
                f.write("\n")  # Empty line to separate file entries
        return gist_file_path

    def load_code_files(self, gist_file_path=None):
        if gist_file_path is None:
            gist_file_path = os.path.join(self.root_path, self.default_gist_foler, self.default_codefile_gist_file)
        files = []
        with open(gist_file_path, "r") as f:
            content = f.read()
            file_blocks = content.split("\n\n")  # Splitting by double newline to separate file entries
            for block in file_blocks:
                if block.strip():  # Ensure the block is not empty
                    lines = block.split("\n")
                    file_data = {}
                    current_key = None
                    for line in lines:
                        if ": " in line and not line.startswith(" "):  # New key-value pair
                            key, value = line.split(": ", 1)
                            file_data[key] = value
                            current_key = key
                        elif current_key:  # Continuation of previous value
                            file_data[current_key] += "\n" + line

                    if 'Filename' in file_data and 'Path' in file_data and 'Package' in file_data:
                        code_file = CodeFile(file_data['Filename'], file_data['Path'], file_data['Package'])
                        code_file.set_details(
                            file_data.get('Summary', ''),
                            file_data.get('Imports', ''),
                            file_data.get('Functions', ''),
                            file_data.get('TODO Comments', '')
                        )
                        files.append(code_file)

        return files

def print_tree(packages, prefix=''):
    result = ""
    for package, contents in packages.items():
        result += f"{prefix}{package}/\n"
        if 'files' in contents and contents['files']:
            for file in contents['files']:
                result += f"{prefix}    {file}\n"
        if 'sub_packages' in contents:
            result += print_tree(contents['sub_packages'], prefix=prefix + '    ')
    return result