import re
import os
from typing import List, Tuple, Optional
from projectfiles import ProjectFiles
from functions import efficient_file_search, read_files, read_packages, process_file_request, get_static_notes
from llm_client import LLMQueryManager

# the global search results dict with key being the search keyword, the value being a list of file names, or [] if no matching files
# this is important to avoid repeated search for the same keyword
global_search_results = {}

def search_results_to_prompt(search_results: dict = None) -> str:
    # print the search results in the format that can be used in the LLM prompt
    # keyword: [file1, file2]
    # or
    # keyword: not found in project
    if not search_results:
        search_results = global_search_results
    result_str = ""
    for keyword, files in search_results.items():
        if files:
            result_str += f"{keyword}: {files}\n"
        else:
            result_str += f"{keyword}: not found in project\n"
    return result_str

def initiate_llm_query_manager(pf: Optional[ProjectFiles], system_prompt, reused_prompt_template):
    use_llm = os.environ.get("LLM_USE")
    # prompts can be reused and cached in the LLM if it is supported
    if pf is not None:
        package_notes = get_static_notes(pf)
        project_tree = pf.to_tree()
    else:
        project_tree = ""
        package_notes = ""
    if reused_prompt_template is not None:
        cached_prompt = reused_prompt_template.format(project_tree=project_tree, package_notes=package_notes)
    else:
        cached_prompt = None
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager

def process_llm_response(last_response: str, pf: ProjectFiles) -> Tuple[str, List[str], str]:
    """
    process the response from LLM during the conversation, take ations based on the response including searching files, reading files, reading packages
    
    Args:
    last_response: the last response from the LLM
    pf: ProjectFiles object

    Returns:
    additional_reading: additional reading materials based on the LLM response
    processed_requests: list of processed requests
    updated_last_response: updated last response without the "**Next Steps**" section
    """

    additional_reading = ""
    processed_requests = []
    # Find the last "**Next Steps**" section
    next_steps = last_response.split("**Next Steps**")[-1].strip()
    if not next_steps:
        print("No next steps found in the response")
        return additional_reading, processed_requests, last_response
    print(next_steps)
    lines = next_steps.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if "[I need to search" in line:
            what = re.search(r'<keyword>(.*?)</keyword>', line).group(1)
            print(f"LLM needs to search: {what}")
            file_extensions = ['.java', '.yml', '.properties']
            matching_files = []
            if what in global_search_results:
                matching_files = global_search_results[what]
                # if match_files is empty that means the LLM keeps searching for the same keyword but no matching files found
                # this is the case when we are stuck in a loop
                if not matching_files:
                    raise Exception(f"DO NOT SEARCH '{what}' AGAIN, NO MATCHING FILES FOUND")
            else:
                matching_files = efficient_file_search(pf.root_path, what, file_extensions=file_extensions)
                global_search_results[what] = matching_files

            if matching_files:
                files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                additional_reading += f"\nYou requested to search for '{what}'\nHere are results: <files>{files_str}</files>\n"
            else:
                additional_reading += f"\nNo matching files found with '{what}'\n"
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
    # replace the **Next Steps** so that it does not appear in the next prompt
    updated_last_response = last_response.replace("**Next Steps**", "You asked about the following:\n")
    return additional_reading, processed_requests, updated_last_response
