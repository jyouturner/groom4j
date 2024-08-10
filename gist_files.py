import os

import sys
import argparse
from projectfiles import ProjectFiles
from dotenv import load_dotenv
load_dotenv(override=True)

from llm_router import LLMQueryManager

system_prompt = """
You are a world class Java developer. You are given a Java program to maintain. You need to read the code and write notes.
The notes should be short, concise and to the point.
Make sure to include the following points:
- The purpose of the code
- The functionality of the code
- The important classes and methods used in the code

"""

user_prompt_template = """

Just return the notes. DO NOT explain your reason.

File Name: {}

Package: {}

Code:

{}

"""

query_manager = LLMQueryManager(system_prompt=system_prompt)


# the function to generate the summary of the code file
def code_gisting(project_root, code_file, verbose=True) -> str:
    full_path = os.path.join(project_root, code_file.path)
    with open(full_path, 'r') as file:
        code = file.read()
    prompt = user_prompt_template.format(code_file.filename, code_file.package, code)
    summary = query_manager.query(prompt)
    if verbose:
        print(f"Summary of the code file {code_file.filename}: {summary}")
    return summary

# the main function to run the code
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gisting the code files using LLM")
    parser.add_argument("project_root", type=str, help="Path to the project root")
       
    args = parser.parse_args()

    # Convert to absolute path if it's a relative path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)
    pf = ProjectFiles(repo_root_path=root_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    # scan the files in the project, and create package structure
    pf.from_gist_files()
    if pf.files:
        print(f"Gist files already exist at {pf.gist_file_path}, are you sure you want to continue? (y/n)")
        if input() != "y":
            sys.exit(1)
    # now talk with LLM to get the notes of files
    codefiles = pf.get_files_of_project()
    input("Press Enter to continue to send request to LLM ...")
        
    for file in codefiles:
        print(file.filename, file.package, file.path)
        notes = code_gisting(root_path, file)
        file.set_summary(notes)
    # now that we have the notes for each file, we can persist them to a file for future use
    gist_file_path = pf.persist_code_files(codefiles)
    print(f"Gist file is persisted to {gist_file_path}")
    print("Please run the gist_package.py to recreate the package notes.")
