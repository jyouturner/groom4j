from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles

from typing import Union
from functions import get_file, get_package, get_static_notes, efficient_file_search, process_file_request
from functions import read_files, read_packages, read_all_packages, read_from_human
from llm_interaction import process_llm_response, initiate_llm_query_manager, search_results_to_prompt


system_prompt = """
You are a world-class Java developer tasked with grooming development tasks in Java projects. Your goal is to write clear, concise, and specific steps to accomplish tasks, focusing only on development aspects (not testing, deployment, or other tasks).
"""

instructions = """
<instructions>

Follow this structured approach:

1. Task Analysis:
   Before proceeding with the implementation steps, perform the following analysis:
   a) Summarize the main objective of the task in 1-2 sentences.
   b) List the key metrics or issues presented in the task description.
   c) Reframe the task into 3-5 specific questions or investigation points that need to be addressed.
   d) Identify any assumptions or potential misunderstandings in the task description.

   Present your analysis using the following format:
   [Task Summary: Brief summary of the main objective]
   [Key Metrics/Issues: 
    - Metric/Issue 1
    - Metric/Issue 2
    ...]
   [Investigation Points:
    1. Question or point to investigate
    2. Another question or point
    ...]
   [Assumptions/Potential Misunderstandings:
    - Assumption 1
    - Potential misunderstanding 1
    ...]

2. Research the codebase:
    - Review relevant files, classes, and methods
    - Identify any existing code that relates to the task
    - Feel free to ask for specific file contents, package summaries, or code snippets if needed

3. Plan the implementation:
 - Break down the task into logical steps
 - Consider the order of operations and any dependencies between steps
 - Think about potential edge cases or error scenarios

4. Write the steps:
 - Only write the steps when you are confident in your approach
 - Use this format only:
 [Step 1: Brief description]
 [Step 2: Brief description]
 ...
 - Be as specific as possible, mentioning exact file names, method names, or class names where applicable
 - Include any necessary code modifications or additions
 - Provide coding snippets, examples, or best practices to follow when applicable
 - If you have questions that you can not find answer by researching the codebase, you can leave them at the end of the steps. In a section named "Questions".

5. Review and refine:
 - After writing the steps, review them for completeness and clarity
 - Ensure that each step is actionable and specific
 - Consider any potential challenges or risks associated with each step

Remember:
- Explain your reasoning when requesting additional information
- Begin your analysis with the Task Analysis section, then proceed with "Let's break down the task and plan our approach."

</instructions>
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

and summaries of the packages in the project:
{package_notes}
"""

user_prompt_template = """
The task to be groomed is:
"{question}"

<Previous research notes>
{notes}
</Previous research notes>

<Previous search results>
{search_results}
</Previous search results>

<Additional Materials>
{additional_reading}
</Additional Materials>

Please perform a Task Analysis following the structured approach outlined in the instructions, then proceed with analyzing this task and providing a detailed plan.
{instructions}

{function_prompt}
"""



def ask_continue(query_manager, question, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    # capture the DO-NOT_SEARCH Error and update prompt
    updated_last_response = last_response
    stop_function_prompt = False
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
    parser = argparse.ArgumentParser(description="Grooming development task")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--task", type=str, default="", help="Development task, for example 'Add a health check endpoint to the web service'")
    parser.add_argument("--jira", type=str, default="", help="URL of the Jira ticket")
    parser.add_argument("--max-rounds", type=int, default=8, help="Maximum rounds of conversation with LLM before stopping the conversation (default: 8)")
    args = parser.parse_args()
    print(args)

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

    task = args.task
    jira = args.jira
    # one of task or jira should be provided
    if not task and not jira:
        print("Please provide either task or jira")
        sys.exit(1)
    # if jira is provided, then get the task from Jira
    if jira:
        from integration import MyJira
        myJira = MyJira(host=os.environ.get("JIRA_SERVER"), user=os.environ.get("JIRA_USERNAME"), api_token=os.environ.get("JIRA_API_TOKEN"))
        issue = myJira.find_issue(jira)
        task = issue.fields.description
    max_rounds = args.max_rounds
    print(f"Task: {task} max_rounds: {max_rounds}")
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
        #last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager=query_manager, question=task, last_response=last_response, pf=pf, past_additional_reading=past_additional_reading)
        #print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            last_response = response
            i += 1
    print("Conversation with LLM ended")
