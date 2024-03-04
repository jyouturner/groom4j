import os

import sys
import argparse
from projectfiles import ProjectFiles
from dotenv import load_dotenv
load_dotenv(override=True)

from llm_router import query

prompt_shorten_template = """
You are a world class Java developer. You are given a Java program to maintain. You need to read the code and write notes.
The notes should be short, concise and to the point.
Make sure to include the following points:
- The purpose of the code
- The functionality of the code
- The important classes and methods used in the code

Just return the notes. DO NOT explain your reason.

File Name: {}

Package: {}

Code:

{}

"""

# the function to generate the summary of the code file
def code_gisting(code_file, verbose=True) -> str:
    with open(code_file.path, 'r') as file:
        code = file.read()
    prompt = prompt_shorten_template.format(code_file.filename, code_file.package, code)
    summary = query(prompt)
    if verbose:
        print(f"Summary of the code file {code_file.filename}: {summary}")
    return summary

# the main function to run the code
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gisting the code files using LLM")
    parser.add_argument("--project_root", type=str, default="", required= True, help="path to the project root")
       
    args = parser.parse_args()

    root_path = args.project_root
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)
    pf = ProjectFiles(root_path=root_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    # scan the files in the project, and create package structure

    # now talk with LLM to get the notes of files
    codefiles = pf.get_files_of_project()
    input("Press Enter to continue to send request to LLM ...")
        
    for file in codefiles:
        print(file.filename, file.package, file.path)
        notes = code_gisting(file)
        file.set_summary(notes)
    # now that we have the notes for each file, we can persist them to a file for future use
    gist_file_path = pf.persist_code_files(codefiles)
    print(f"Gist file is persisted to {gist_file_path}")
