from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles
from dotenv import load_dotenv
load_dotenv(override=True)

from llm_router import LLMQueryManager, ResponseManager
from typing import Union
from functions import get_file, get_package
from functions import search_files_with_keyword, read_files, read_packages, read_all_packages, read_from_human

system_prompt = """
You are an AI assistant designed to help Java developers understand existing Java projects.
Your task is to analyze the project structure, identify API endpoints, and provide detailed notes on their implementation, with a strong focus on data flow analysis.

For each API endpoint you identify, provide the following information in markdown format:

## [Endpoint Name]

1. **Purpose**: Briefly describe the purpose of this endpoint.

2. **Functionality**: Explain what this endpoint does in detail.

3. **Request Structure**:
   - HTTP Method
   - Path parameters
   - Query parameters
   - Request body (if applicable)

4. **Response Structure**:
   - Response body
   - Possible status codes

5. **Data Flow**:
   - For GET requests: 
     - Explain in detail how data is retrieved, including all database queries and external service calls.
     - Trace the data flow from the initial request to the final response, including any intermediate services or caches.
     - Describe any data transformations that occur along the way.
     - If multiple data sources are involved, explain how the data is aggregated or joined.
   - For POST requests: 
     - Describe how data is processed and saved, step by step.
     - Detail all validations and transformations applied to the incoming data.
     - If data is stored in a database, provide details on the schema and any constraints.
     - Explain any cascading effects or triggers that might be activated by the data change.

6. **Data Processing**: 
   - Detail all transformations or business logic applied to the data.
   - Explain any caching mechanisms used and how they affect data retrieval or storage.
   - Describe any asynchronous processing or background jobs triggered by this endpoint.

7. **Key Classes/Methods**: 
   - List the main classes and methods involved in handling this endpoint.
   - For each key method, briefly explain its role in the data flow.

8. **Notable Design Patterns or Architectural Choices**: 
   - Highlight any interesting implementation details.
   - Explain how these choices affect the data flow or system performance.

9. **Error Handling and Edge Cases**:
   - Describe how errors are handled at different stages of the data flow.
   - Explain any retry mechanisms or circuit breakers in place.

10. **Performance Considerations**:
    - Discuss any optimizations in place for data retrieval or processing.
    - Mention any potential performance bottlenecks in the data flow.

Provide code snippets and file locations where relevant. If you need more information to complete any section, ask for it using the following format:

[I need to search <keyword>keywords</keyword> in project]
[I need content of files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
[I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]

If you encounter unclear or complex code, state your assumptions and any potential alternative interpretations. Always err on the side of providing more detail, especially when it comes to data flow analysis.

Prioritize thoroughness over speed. If the project is large, focus on the most important or frequently used endpoints first, but ensure that the data flow analysis for each endpoint is as complete as possible.

You must follow exactly the above specified format for requests and structure your response using markdown.
"""
user_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}



Previous research notes:
{notes}

Additional reading:
{additional_reading}


"""

def initiate_llm_query_manager(pf):
    use_llm = os.environ.get("USE_LLM")
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=None)
    
    return query_manager

default_api_notes_file = "api_notes.md"

def ask_continue(query_manager, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    projectTree = pf.to_tree()
    additional_reading = ""
    for line in last_response.split("\n"):
        if line.startswith("[I need to search"):
            # [I need to search <search>what you need to search</search>]
            what = re.search(r'<keyword>(.*?)</keyword>', line).group(1)
            print(f"LLM needs to search: {what}")
            # search for files with the keyword within the project
            files = search_files_with_keyword(pf.root_path, what)
            for file in files:
                additional_reading += f"Found {what} in file: {file}\n"
            additional_reading += f"Found {len(files)} files with the keyword: {what}\n "
        elif line.startswith("[I need content of files:") or line.startswith("[I need access files:"):
            # example [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
            # Define a regex pattern to match content between <file> and </file> tags
            pattern = r'<file>(.*?)</file>'
            file_names = re.findall(pattern, line)
            print(f"LLM needs access to files: {file_names}")
            additional_reading += read_files(pf, file_names)
            print(f"contents provided for {file_names}")            
        elif line.startswith("[I need info about packages:"):
            # [I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]
            pattern = r'<package>(.*?)</package>'
            package_names = re.findall(pattern, line)
            print(f"Need more info of package: {package_names}")
            additional_reading += read_packages(pf, package_names)
        elif line.startswith("[I need clarification about"):
            # [I need clarification about <ask>what you need clarification about</ask>]
            what = re.search(r'<ask>(.*?)</ask>', line).group(1)
            print(f"LLM needs more information: \n{what}")
            # ask user to enter manually through commmand line
            additional_reading += f"Regarding {what}, {read_from_human(line)}\n"
        elif line.startswith("[I need"):
            print(f"LLM needs more information: \n{line}")
            additional_reading += f"{read_from_human(line)}\n"
        else:
            pass
    if last_response=="" or additional_reading:
        # either the first time or the last conversation needs more information
        if last_response=="":
            # this is the initial conversation with LLM, we just pass the whole package notes.
            package_notes_str = read_all_packages(pf)
            last_response = package_notes_str
            
        user_prompt = user_prompt_template.format(project_tree = projectTree, notes = last_response, additional_reading = "Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
        # request user click any key to continue
        # input("Press Enter to continue to send message to LLM ...")
        response = query_manager.query(user_prompt)
        return response, additional_reading, False
    else:
        print("the LLM does not need any more information, so we can end the conversation")
        return last_response, None, True
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--max-rounds", type=int, default=8, required= False, help="default 8, maximam rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()

    # Convert to absolute path if it's a relative path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(repo_root_path=root_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    # load the files and package gists from persistence.
    pf.from_gist_files()
   
    max_rounds = args.max_rounds

    # looping until the user is confident of the steps and instructions, or 8 rounds of conversation
    i = 0
    past_additional_reading = ""
    doneNow = False
    additional_reading = ""
    ResponseManager.reset_prompt_response()
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf)
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager, last_response, pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1
    # save to a gist file
    api_notes = response
    api_notes_file = os.path.join(pf.root_path, ProjectFiles.default_gist_foler, default_api_notes_file)
    with open(api_notes_file, "w") as file:
        file.write(api_notes)
