import re
import os
from typing import List, Tuple
from projectfiles import ProjectFiles
from functions import efficient_file_search, read_files, read_packages, process_file_request, get_static_notes
from llm_client import LLMQueryManager

def initiate_llm_query_manager(pf, system_prompt, reused_prompt_template):
    use_llm = os.environ.get("USE_LLM")
    # prompts can be reused and cached in the LLM if it is supported
    package_notes = get_static_notes(pf)
    project_tree = pf.to_tree()
    cached_prompt = reused_prompt_template.format(project_tree=project_tree, package_notes=package_notes)
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager

def process_llm_response(last_response: str, pf: ProjectFiles) -> Tuple[str, List[str]]:
    additional_reading = ""
    processed_requests = []
    
    lines = last_response.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "[I need to search" in line:
            what = re.search(r'<keyword>(.*?)</keyword>', line).group(1)
            print(f"LLM needs to search: {what}")
            file_extensions = ['.java', '.yml', '.properties']
            matching_files = efficient_file_search(pf.root_path, what, file_extensions=file_extensions)

            if matching_files:
                files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>{files_str}</files>\n</search>\n"
            else:
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>No matching files found</files>\n</search>\n"
            processed_requests.append(f"Search for '{what}'")

        elif "[I need content of files:" in line or "[I need access files:" in line:
            file_names = process_file_request(lines[i:])
            print(f"LLM needs access to files: {file_names}")
            additional_reading += read_files(pf, file_names)
            print(f"contents provided for {file_names}")
            while i < len(lines) and "]" not in lines[i]:
                i += 1
            processed_requests.append(f"Access files: {', '.join(file_names)}")

        elif "[I need info about packages:" in line:
            pattern = r'<package>(.*?)</package>'
            package_names = re.findall(pattern, line)
            print(f"Need more info of package: {package_names}")
            additional_reading += read_packages(pf, package_names)
            print(f"info provided for {package_names}")
            processed_requests.append(f"Package info: {', '.join(package_names)}")

        i += 1
    
    return additional_reading, processed_requests
