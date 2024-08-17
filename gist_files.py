import os
import sys
import argparse
from projectfiles import ProjectFiles
import re

from dotenv import load_dotenv
load_dotenv(override=True)

from llm_client import LLMQueryManager

system_prompt = """
You are a world-class developer and configuration expert. When analyzing a file, provide a detailed summary focusing on the following aspects:

For Java files:
- The overall purpose of the file/class
- Key functionalities and their implementations
- Important methods: their signatures, parameters, return types, and a brief description of what they do
- Any notable design patterns or architectural choices
- Interactions with other parts of the system (e.g., database calls, API interactions)
- Exception handling and error management strategies
- Any complex algorithms or business logic
- Use of important libraries or frameworks

For configuration files (properties, YAML, XML):
- The overall purpose of the configuration file
- Key configurations and their significance
- Any environment-specific settings
- Hierarchical structures and their importance
- References to other configuration files or properties
- Any sensitive information (noting its presence, not the actual values)

For test files:
- The class or functionality being tested
- Key test scenarios covered
- Any notable testing frameworks or techniques used
- Mock objects or test data setup

For all files:
- Any TODO comments or areas marked for improvement
- Potential performance considerations
- Security implications, if any

Provide a concise yet comprehensive summary that captures these details. Focus on aspects that would be most helpful for a developer trying to understand and potentially modify this code.
"""

user_prompt_template = """
Provide a detailed summary of the following file:

File Name: {filename}
File Type: {filetype}
Package/Location: {package}

Imports:
{imports}

Functions/Methods:
{functions}

TODO Comments:
{todo_comments}

Full File Content:

{content}

Please analyze this file based on the guidelines provided earlier, focusing on key functionalities, important methods, design patterns, and other crucial details.
"""

def initiate_llm_query_manager(pf):
    use_llm = os.environ.get("USE_LLM")
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=None)
    
    return query_manager


def get_file_type(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower()

def code_gisting(query_manager, project_root, code_file, verbose=True) -> str:
    full_path = os.path.join(project_root, code_file.path)
    with open(full_path, 'r') as file:
        content = file.read()
    
    file_type = get_file_type(code_file.filename)
    
    # Extract additional context
    imports = extract_imports(content)
    functions = extract_functions(content, file_type)
    todo_comments = extract_todo_comments(content)
    
    prompt = user_prompt_template.format(
        filename=code_file.filename,
        filetype=file_type,
        package=code_file.package,
        content=content,
        imports=imports,
        functions=functions,
        todo_comments=todo_comments
    )
    
    summary = query_manager.query(prompt)
    if verbose:
        print(f"Summary of the file {code_file.filename}: {summary}")
    return summary

def extract_imports(content):
    # Simple regex to extract import statements
    import_pattern = r'^import .*?;'
    imports = re.findall(import_pattern, content, re.MULTILINE)
    return "\n".join(imports)

def extract_functions(content, file_type):
    if file_type == '.java':
        # Simple regex to extract method signatures (this can be improved)
        function_pattern = r'(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])'
        functions = re.findall(function_pattern, content)
        return "\n".join([" ".join(func).strip() for func in functions])
    # Add extractors for other file types as needed
    return ""

def extract_todo_comments(content):
    # Simple regex to extract TODO comments
    todo_pattern = r'//\s*TODO:?.*'
    todos = re.findall(todo_pattern, content)
    return "\n".join(todos)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gisting the code files using LLM")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    
    args = parser.parse_args()

    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(
        repo_root_path=root_path,
        prefix_list=["src/main/java", "src/main/resources"],
        suffix_list=[".java"],
        resource_suffix_list=['.properties', '.yaml', '.yml', '.xml']
    )

    print("Initializing ProjectFiles...")
    pf.from_project()

    print(f"\nJava files to process: {len(pf.files)}")
    print(f"Resource files to process: {len(pf.resource_files)}")

    all_files = pf.files + pf.resource_files
    total_files = len(all_files)

    print(f"\nTotal files to process: {total_files}")

    if pf.gist_file_path and os.path.exists(pf.gist_file_path):
        print(f"Gist files already exist at {pf.gist_file_path}")
        print("Do you want to update existing gists or create new ones?")
        choice = input("Enter 'update' to update existing gists, or 'new' to create new ones: ").lower()
        if choice == 'update':
            all_files = [f for f in all_files if not f.summary]
            print(f"Updating {len(all_files)} files without existing summaries.")
        elif choice != 'new':
            print("Invalid choice. Exiting.")
            sys.exit(1)

    input(f"Press Enter to start gisting {len(all_files)} files...")
    query_manager = initiate_llm_query_manager(pf)
    for index, file in enumerate(all_files, start=1):
        print(f"Processing file {index}/{total_files}: {file.filename} ({file.package})")
        notes = code_gisting(query_manager=query_manager, project_root=root_path, code_file=file)
        file.set_summary(notes)

    gist_file_path = pf.persist_code_files(all_files)
    print(f"Gist file is persisted to {gist_file_path}")

    # Optionally, you can print out the first few lines of the gist file to verify its contents
    print("\nFirst few lines of the gist file:")
    with open(gist_file_path, 'r') as f:
        print(f.read(500))  # Print first 500 characters

    print("\nGisting process completed.")