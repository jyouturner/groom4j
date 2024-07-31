from collections import defaultdict
import os
import sys
from dotenv import load_dotenv
import time

import argparse
from projectfiles import ProjectFiles
# load env before importing LLM functions
load_dotenv(override=True)
from llm_router import query


prompt_pacakge_notes_template = """
You are a world class Java developer. You are given a legacy code base to maintain. 
You already read the code and wrote notes about the code files. Now you need to write notes about the packages.
Below you are given the notes of the code files in the package, as well as the notes of its sub-packages.
Make sure to include the following points:
- The purpose of the package

Just return the notes.
DO NOT explain your reason.

Package Name: {}

Notes of Sub Packages: 
{}

Notes of Direct Child Files: 
{}

"""

def real_package_gisting(package, subpackage_notes, filenotes):
    print(f"\n\nchecking LLM on package: {package}")
    prompt = prompt_pacakge_notes_template.format(package, subpackage_notes, filenotes)
    notes = query(prompt)
    return notes


# Main function to run the code
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gisting the Packages using LLM")
    parser.add_argument("--project_root", type=str, default="", required= True, help="path to the project root")
       
    args = parser.parse_args()

    # if args.project_root is relative path, then get the absolute path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)
    pf = ProjectFiles(repo_root_path=root_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    # load the existing gist files in the project, and create package structure
    pf.from_gist_files()
    # since we already have the summary of the individual code files, next we ask LLM to summarize the packages
    print("\n" + "-" * 10 + "\nTravers Bottom-Up to get notes on packages:")
    pf.package_gisting = real_package_gisting
    pf.package_structure_traverse(packages=None, action_file=pf.execute_on_file, action_package=pf.execute_on_package, is_bottom_up=True)
    # persist the package notes
    file = pf.persist_package_notes()
    print(f"Package notes are persisted to {file}")
