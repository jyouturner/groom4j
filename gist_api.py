from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles

from typing import Union
from functions import get_file, get_package, efficient_file_search, process_file_request, get_static_notes
from functions import read_files, read_packages, read_all_packages, read_from_human
from llm_interaction import process_llm_response, initiate_llm_query_manager, search_results_to_prompt


system_prompt = """
You are an AI assistant designed to help Java developers understand existing Java projects.
"""

instructions = """
If you encounter unclear or complex code, state your assumptions and any potential alternative interpretations. Always err on the side of providing more detail, especially when it comes to data flow analysis.

Prioritize thoroughness over speed. If the project is large, focus on the most important or frequently used endpoints first, but ensure that the data flow analysis for each endpoint is as complete as possible.

You must follow exactly the above specified format for requests and structure your response using markdown.

"""

function_prompt = """
If you need more information, use the following formats to request it:

1. To search for keywords, request them in this specific format only:
   [I need to search for keywords: <keyword>keyword1</keyword>, <keyword>keyword2</keyword>]
   Then I will provide the files that contain the keywords, in format:
   ```text
    You requested to search for : [keyword]
    Here are the results:<files><file>file1.java</file>, <file>file2.java</file></files>
   ``` 
    or if no files are found, I will let you know as well. Therefore you should check the additional notes to avoid requesting again:
    ```text
    No matching files found with [keyword]
    ```

2. To request file contents, request them in this specific format only:
   [I need content of files: <file>file1.java</file>, <file>file2.java</file>]
   Then I will provide summary and content of the file next with format:
    <file name="file name">
        <summary>summary of file</summary>
        <content> file content </content>
    </file>
    or if the file is not found and you should not request again.

3. To get information about packages, request them in this specific format only:
   [I need info about packages:: <package>com.example.package1</package>, <package>com.example.package2</package>]
    Then I will provide summary of the package next with format:
    <package name="package name">
        <notes>summary of package</notes>
        <sub_packages>sub packages</sub_packages>
        <files>files in the package</files>
    </package>

Ask for additional information at end of the response, with the following format:

```text
**Next Steps**
[your request to search for keywords]
[your request to read files]
[your request to read packages]
...
```

After receiving information, analyze it and relate it back to the original question. 

Answer to your requests including search results, file contents and package summaries will be found within 
<Additional Materials>
...
<Additional Materials> tags.

```
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

{search_results}

{instructions}

{function_prompt}
"""

# very specific to this script
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


def ask_continue(query_manager, question, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    # capture the DO-NOT_SEARCH Error and update prompt
    updated_last_response = last_response
    stop_function_prompt = False
    additional_reading = ""
    try:
        additional_reading, processed_requests, updated_last_response = process_llm_response(last_response, pf)
    except Exception as e:
        if "DO NOT SEARCH" in str(e):
            # the conversation is going in a loop, so we need to stop it, by removing the function prompt
            print("The LLM is stuck in a loop, so we need to stop it")
            stop_function_prompt = True
        else:
            raise e
    
    if last_response == "" or additional_reading:
        user_prompt = user_prompt_template.format(
            question=question,
            notes=updated_last_response,
            search_results=search_results_to_prompt(),
            additional_reading="Below are the additional info that you should read before answering questions:\n" + str(past_additional_reading) + "\n\n" + str(additional_reading) if not stop_function_prompt else "",
            instructions=instructions,
            function_prompt=function_prompt if not stop_function_prompt else "",
        )
        response = query_manager.query(user_prompt)
        return response, additional_reading, False
    else:
        print("The LLM does not need any more information, so we can end the conversation")
        return last_response, None, True
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--max-rounds", type=int, default=8, required= False, help="default 8, maximam rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()

    # the order of the following imports is important
    # since the initialization of langfuse depends on the os environment variables
    # which are loaded in the config_utils module
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager, ResponseManager
    from llm_interaction import process_llm_response, initiate_llm_query_manager

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
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template)
    last_response = ""
    while True and i < max_rounds:
        
        response, additional_reading, doneNow = ask_continue(query_manager, question=question, last_response=last_response, pf=pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            last_response = response
            i += 1
    # save to a gist file
    default_api_notes_file = "api_notes.md"
    api_notes = response
    api_notes_file = os.path.join(pf.root_path, ProjectFiles.default_gist_foler, default_api_notes_file)
    with open(api_notes_file, "w") as file:
        file.write(api_notes)