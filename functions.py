from typing import Tuple
import os

#
# here are the functions to be used in the pipeline.
#

def ask_for_file(pf, file_name, package=None) -> Tuple[str, str, str, str]:
    """
    given a file name, return the file name, summary, path, and content of the file
    """
    file = pf.find_codefile_by_name(file_name, package)
    if file:
        # now let's get the file content, since we have the path
        with open(file.path, "r") as f:
            file_content = f.read()
        return file.filename, file.summary, file.path, file_content
    else:
        return None, None, None, None
    
def ask_for_files(pf, file_names) -> Tuple[Tuple[str, str, str, str]]:
    files = []
    for file_name in file_names:
        # clean it
        file_name = file_name.strip()
        filename, summary, path, content = ask_for_file(pf, file_name)
        if filename:
            files.append((filename, summary, path, content))
    return files

def ask_for_package(pf, package_name) -> Tuple[str, str, str, str]:
    """
    given a package name, return the package name, notes, sub-packages, and file-names
    """
    notes = pf.find_notes_of_package(package_name.strip())
    subpackages, codefiles = pf.find_subpackages_and_codefiles(package_name)
    subpacakgenames = ', '.join(subpackages)
    codefilenames = ', '.join([f.filename for f in codefiles])
    return package_name, notes, subpacakgenames, codefilenames

def ask_for_packages(pf, package_names) -> Tuple[Tuple[str, str, str, str]]:
    packages = []
    for package_name in package_names:
        # clean it
        package_name = package_name.strip()
        package, notes, subpacakgenames, codefilenames = ask_for_package(pf, package_name)
        if package:
            packages.append((package, notes, subpacakgenames, codefilenames))
    return packages
    