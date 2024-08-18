from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles
from dotenv import load_dotenv
load_dotenv(override=True)

from llm_client import LLMQueryManager, ResponseManager
from typing import Union
from functions import get_file, get_package, efficient_file_search, process_file_request, get_static_notes
from functions import read_files, read_packages, read_all_packages, read_from_human

system_prompt = """
You are an AI assistant designed to help Java developers understand existing Java projects.
You will be given a specific question to investigate the Java codebase.
If you need more information to complete any section, ask for it using the following format:

1. To search for keywords, request them in this specific format only:
   [I need to search for keywords: <keyword>keyword1</keyword>, <keyword>keyword2</keyword>]
   Then I will provide the files that contain the keywords, in format:
    <search><keyword>keyword</keyword>
    <files><file>file1.java</file>, <file>file2.java</file></files>
    </search>

2. To request file contents, request them in this specific format only:
   [I need content of files: <file>file1.java</file>, <file>file2.java</file>]
   Then I will provide summary and content of the file next with format:
    <file name="file name">
        <summary>summary of file</summary>
        <content> file content </content>
    </file>

3. To get information about packages, request them in this specific format only:
   [I need info about packages:: <package>com.example.package1</package>, <package>com.example.package2</package>]
    Then I will provide summary of the package next with format:
    <package name="package name">
        <notes>summary of package</notes>
        <sub_packages>sub packages</sub_packages>
        <files>files in the package</files>
    </package>

Always use these exact formats for requests. After receiving information, analyze it and relate it back to the original question. If you need clarification on any information received, ask for it specifically.

During our conversations, your previous notes will be found
<Previous research notes> previous research notes </Previous research notes>tags, 
and any answer to your requests including search results, file contents and package summaries will be found within 
<Additional Materials>
...
<Additional Materials> tags.

If you encounter unclear or complex code, state your assumptions and any potential alternative interpretations. Always err on the side of providing more detail, especially when it comes to data flow analysis.

Prioritize thoroughness over speed. If the project is large, focus on the most important or frequently used endpoints first, but ensure that the data flow analysis for each endpoint is as complete as possible.

You must follow exactly the above specified format for requests and structure your response using markdown.
"""

reused_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}
end of project tree

and summaries of the packages in the project:
{package_notes}
end of package notes
"""

user_prompt_template = """

{question}

<Previous research notes>
{notes}
</Previous research notes>

<Additional Materials>
{additional_reading}
</Additional Materials>
"""

question = """
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

Provide code snippets and file locations where relevant.
"""

def initiate_llm_query_manager(pf):
    use_llm = os.environ.get("USE_LLM")
    # prompts can be reused and cached in the LLM if it is supported
    package_notes = get_static_notes(pf)
    project_tree = pf.to_tree()
    cached_prompt = reused_prompt_template.format(project_tree=project_tree, package_notes=package_notes)
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager



def ask_continue(query_manager, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    additional_reading = ""
    lines = last_response.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "[I need to search" in line:
            # [I need to search <search>what you need to search</search>]
            what = re.search(r'<keyword>(.*?)</keyword>', line).group(1)
            print(f"LLM needs to search: {what}")
            # search for files with the keyword within the project
            # search for files with the keyword within the project
            file_extensions = ['.java', '.yml', '.properties']  # Add or modify as needed
    
            matching_files = efficient_file_search(pf.root_path, what, file_extensions=file_extensions)

            if matching_files:
                files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>{files_str}</files>\n</search>\n"
            else:
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>No matching files found</files>\n</search>\n"
        elif "[I need content of files:" in line or "[I need access files:" in line:
            file_names = process_file_request(lines[i:])
            print(f"LLM needs access to files: {file_names}")
            additional_reading += read_files(pf, file_names)
            print(f"contents provided for {file_names}")
            # Skip processed lines
            while i < len(lines) and "]" not in lines[i]:
                i += 1            
        elif "[I need info about packages:" in line:
            # [I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]
            pattern = r'<package>(.*?)</package>'
            package_names = re.findall(pattern, line)
            print(f"Need more info of package: {package_names}")
            additional_reading += read_packages(pf, package_names)
            print(f"packages provided for {package_names}")
        #elif line.startswith("[I need clarification about"):
            # [I need clarification about <ask>what you need clarification about</ask>]
        #    what = re.search(r'<ask>(.*?)</ask>', line).group(1)
        #    print(f"LLM needs more information: \n{what}")
            # ask user to enter manually through commmand line
        #    additional_reading += f"Regarding {what}, {read_from_human(line)}\n"
        #elif line.startswith("[I need"):
        #    print(f"LLM needs more information: \n{line}")
        #    additional_reading += f"{read_from_human(line)}\n"
        else:
            pass
        i += 1
    if last_response=="" or additional_reading:
        # either the first time or the last conversation needs more information
        user_prompt = user_prompt_template.format(question = question, 
                                                  notes = last_response if last_response else "this is the beginning of my research, I need to work hard", 
                                                  additional_reading = past_additional_reading + "\n\n" + additional_reading)
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

    pf = ProjectFiles(repo_root_path=root_path)
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
        #print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1
    # save to a gist file
    default_api_notes_file = "api_notes.md"
    api_notes = response
    api_notes_file = os.path.join(pf.root_path, ProjectFiles.default_gist_foler, default_api_notes_file)
    with open(api_notes_file, "w") as file:
        file.write(api_notes)
