import os
import sys

import argparse
from projectfiles import ProjectFiles


system_prompt = """
You are a world-class software architect and developer. You are analyzing a codebase that includes both Java code and configuration files. Your task is to write comprehensive notes about each package in the project.

For each package, consider the following points:
- The overall purpose of the package
- The main functionalities or services provided by the package
- Key classes or configurations within the package and their roles
- Relationships with other packages (if apparent from the sub-package notes)
- Any notable patterns, design principles, or architectural decisions evident in the package structure

If the package includes non-Java files (like configurations), also consider:
- The role of these configuration files in the package
- How they relate to or support the Java code in the package

Provide a concise yet informative summary that gives a clear understanding of the package's role in the overall project structure.
"""

user_prompt_template = """
Package Name: {package_name}

Notes of Sub Packages: 
{subpackage_notes}

Notes of Direct Child Files: 
{file_notes}

Please provide a comprehensive summary of this package based on the information above.
"""

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()
from llm_client import LLMQueryManager, ResponseManager
from llm_interaction import process_llm_response, initiate_llm_query_manager

query_manager = initiate_llm_query_manager(pf=None, system_prompt=system_prompt, reused_prompt_template=None)

def real_package_gisting(package, subpackage_notes, filenotes):
    print(f"\n\nAnalyzing package: {package}")
    prompt = user_prompt_template.format(
        package_name=package,
        subpackage_notes=subpackage_notes,
        file_notes=filenotes
    )
    notes = query_manager.query(prompt)
    return notes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gisting the Packages using LLM")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    
    args = parser.parse_args()



    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(
        repo_root_path=root_path,
    )

    # Load existing gist files and create package structure
    pf.from_gist_files()

    if not pf.files and not pf.resource_files:
        print("No gist files found. Please run gist_files.py first.")
        sys.exit(1)

    print("\n" + "-" * 50)
    print("Traversing Bottom-Up to generate package summaries:")
    print("-" * 50)


    pf.package_gisting_func = real_package_gisting

    # Traverse the package structure to generate summaries
    pf.package_structure_traverse(
        packages=None,
        action_file_func=pf.check_code_file_exists,
        action_package_func=pf.gist_package,
        is_bottom_up=True
    )

    # Persist the package notes
    package_notes_file = pf.persist_package_notes()
    print(f"\nPackage summaries have been persisted to: {package_notes_file}")

    print("\nPackage gisting complete!")