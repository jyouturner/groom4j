import os
import sys
import argparse
from .projectfiles import ProjectFiles
import re
import time
import json

# Read the Java analysis prompt template
def load_java_analysis_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), 'java-semantic-analysis-phase1-prompt.md')
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Java analysis prompt template not found at {prompt_path}")
    with open(prompt_path, 'r') as f:
        return f.read()

system_prompt = """
You are a world-class developer, and you have been tasked to research a code file.
"""

def get_file_type(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower()

def code_gisting(pf, query_manager, project_root, code_file, gist_file_path, verbose=True) -> str:
    if pf is None:
        raise ValueError("No ProjectFiles instance provided. Skipping persistence.")
    
    full_path = os.path.join(project_root, code_file.path)
    if not os.path.exists(full_path):
        print(f"Error: {full_path} does not exist")
        return ""
        
    with open(full_path, 'r') as file:
        content = file.read()
    
    file_type = get_file_type(code_file.filename)
    
    if file_type == '.java':
        # Use the Java analysis prompt template
        prompt_template = load_java_analysis_prompt()
        # Replace the placeholder with actual file content
        prompt = prompt_template.replace("{file_content}", content)
    else:
        # Skip non-Java files for now
        print(f"Skipping non-Java file: {code_file.filename}")
        return ""

    # Get JSON response from LLM
    json_summary = query_manager.query(prompt)
    
    try:
        # Parse the JSON response
        summary_obj = json.loads(json_summary)
        
        # Convert JSON to a formatted string summary for persistence
        summary = (
            f"Type: {summary_obj.get('file_type', 'UNKNOWN')}\n"
            f"Primary Responsibility: {summary_obj.get('primary_responsibility', '')}\n"
            f"Implements: {', '.join(summary_obj.get('implements', []))}\n"
            f"Extends: {summary_obj.get('extends', '')}\n"
            f"Annotations: {', '.join(summary_obj.get('annotations', []))}\n\n"
            f"Specific Details:\n"
        )
        
        # Add specific details based on file type
        if 'specific_details' in summary_obj:
            for key, value in summary_obj['specific_details'].items():
                if isinstance(value, list):
                    summary += f"{key}:\n"
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                summary += f"  - {k}: {v}\n"
                        else:
                            summary += f"  - {item}\n"
                else:
                    summary += f"{key}: {value}\n"
        
        # Add architectural patterns
        if 'architectural_patterns' in summary_obj:
            summary += "\nArchitectural Patterns:\n"
            for key, value in summary_obj['architectural_patterns'].items():
                if isinstance(value, list):
                    summary += f"{key}: {', '.join(value)}\n"
                else:
                    summary += f"{key}: {value}\n"

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON response for {code_file.filename}. Using raw response.")
        summary = json_summary
    
    if verbose:
        print(f"Summary of the file {code_file.filename}: {summary}")

    # Set the summary and persist immediately
    code_file.set_summary(summary)
    
    pf.persistence.append_code_file(code_file, gist_file_path)
    
    if verbose:
        print(f"Extracted and persisted summary for {code_file.filename}")
    return summary

def main(project_root=None):
    parser = argparse.ArgumentParser(description="Gisting the code files using LLM")
    if project_root is None:
        parser.add_argument("project_root", type=str, help="Path to the project root")
        args = parser.parse_args()
        project_root = args.project_root

    # the order of the following imports is important
    # since the initialization of langfuse depends on the os environment variables
    # which are loaded in the config_utils module
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager
    from llm_utils import initiate_llm_query_manager

    root_path = os.path.abspath(project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(
        repo_root_path=root_path,
        prefix_list=["src/main/java"],  # Only process Java files
        suffix_list=[".java"],
        resource_suffix_list=[]  # No resource files for now
    )

    print("Initializing ProjectFiles...")
    pf.from_project()

    print(f"\nJava files to process: {len(pf.files)}")
    total_files = len(pf.files)

    print(f"\nTotal files to process: {total_files}")

    # Check for existing gist file and handle resumption
    if pf.gist_file_path and os.path.exists(pf.gist_file_path):
        file_size = os.path.getsize(pf.gist_file_path)
        if file_size > 0:
            print(f"Found existing gist file at {pf.gist_file_path}")
            # Load existing gists to avoid reprocessing
            existing_files = pf.load_code_files(pf.gist_file_path)
            processed_paths = {f.path for f in existing_files if f.summary}
            skipped_files = [f for f in pf.files if f.path in processed_paths]
            pf.files = [f for f in pf.files if f.path not in processed_paths]
            
            if len(skipped_files) > 0:
                print(f"Resuming process - found {len(skipped_files)} already processed files")
                print(f"Remaining files to process: {len(pf.files)}")
        else:
            print("Found empty gist file, starting fresh")
    else:
        # Create new empty gist file
        os.makedirs(os.path.dirname(pf.gist_file_path), exist_ok=True)
        open(pf.gist_file_path, 'w').close()
        print("Created new gist file")

    if len(pf.files) == 0:
        print("No files left to process. Exiting.")
        sys.exit(0)

    input(f"Press Enter to start gisting {len(pf.files)} files...")
    query_manager = initiate_llm_query_manager(pf=pf, system_prompt=system_prompt, reused_prompt_template=None, tier="tier2")
    
    for index, file in enumerate(pf.files, start=1):
        print(f"Processing file {index}/{total_files}: {file.filename} ({file.package})")
        try:
            notes = code_gisting(
                pf=pf,
                query_manager=query_manager, 
                project_root=root_path, 
                code_file=file,
                gist_file_path=pf.gist_file_path
            )
            # sleep for a short duration to avoid rate limiting
            time.sleep(1)
        except Exception as e:
            print(f"Error processing file {file.filename}: {str(e)}")
            continue

    print("\nGisting process completed.")
    print(f"Gist file is available at {pf.gist_file_path}")

    # Optionally, you can print out the first few lines of the gist file to verify its contents
    print("\nFirst few lines of the gist file:")
    with open(pf.gist_file_path, 'r') as f:
        print(f.read(500))  # Print first 500 characters

if __name__ == "__main__":
    main()