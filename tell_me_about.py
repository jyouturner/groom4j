from typing import Tuple
import os
import sys
import re
import argparse
import yaml
from projectfiles import ProjectFiles
import time
from typing import Union, Optional
from functions import get_file, get_package, get_static_notes
from functions import efficient_file_search, read_files, read_packages, read_all_packages, read_from_human
from functions import process_file_request
from rewrite_question import decompose_question, system_prompt_rewrite_question

system_prompt = """
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

"""

instructions = """
Begin your analysis with: "Let's inspect the Java project to answer the question: [restate the question]"

<guidelines>
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure, codebase.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly.
5. The goal is to be **as thorough as possible** to help developers plan for maintenance tasks more effectively.
</guidelines>

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

Task: <question>{question}</question>

<Previous research notes>
{notes}
</Previous research notes>

<Previous search results>
{search_results}
</Previous search results>

<Additional Materials>
{additional_reading}
</Additional Materials>

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
    
    if updated_last_response == "" or additional_reading:
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
        return updated_last_response, None, True

def answer_question(pf: Optional[ProjectFiles] , question, past_additional_reading = "", max_rounds=8):
    """
    Given a question, answer it by interacting with the LLM.

    Args:
        pf: The ProjectFiles object.
        question (str): The question to be answered.
        past_additional_reading (str): The additional reading from previous questions.
        max_rounds (int): The maximum number of rounds of conversation with LLM before stopping the conversation. 

    """
    i = 0
    doneNow = False
    additional_reading = ""
    ResponseManager.reset_prompt_response()
    
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template)
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager, question, last_response, pf, past_additional_reading=past_additional_reading)
        #print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            return response
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1

def save_response_to_markdown(question: str, response: str, root_path: str) -> str:
    """
    Save the response to a markdown file.

    Args:
        question (str): The question string used to generate the filename.
        response (str): The response content to be saved in the file.
        root_path (str): The root directory where the file will be saved.

    Returns:
        str: The path to the saved markdown file.
    """
    result_file = re.sub(r"[^a-zA-Z0-9]", "_", question.lower()) + "_" + str(int(time.time())) + ".md"
    result_file = os.path.join(root_path, result_file)
    with open(result_file, "w") as f:
        f.write(response)
    return result_file

def break_down_and_answer(question: str, pf: Optional[ProjectFiles], root_path: str, max_rounds=10) -> None:
    """
    Rewrite the question, answer the decomposed questions, and save the responses to markdown files.

    Args:
        question (str): The original question to be processed.
        pf: The ProjectFiles object.
        root_path (str): The root directory where the files will be saved.
        max_rounds: max rounds of conversation with LLM before exit.
    """
    query_manager = initiate_llm_query_manager(pf=None, system_prompt=system_prompt_rewrite_question, reused_prompt_template=None)
    decompose_questions, refined_question = decompose_question(query_manager, question)
    
    # Record the answers to the decomposed questions
    research_notes = ""
    for q in decompose_questions:
        print(f"Question: {q}")
        response = answer_question(pf, q, past_additional_reading="", max_rounds=max_rounds)
        print(response)
        research_notes += f"\n\nQuestion: {q}\n\n{response}"
        # Write to a markdown file
        result_file = save_response_to_markdown(q, response, root_path)
        print(f"Response saved to {result_file}")

    # Now let's answer the original question
    response = answer_question(pf, refined_question, past_additional_reading=research_notes, max_rounds=args.max_rounds)
    # Save to markdown file
    result_file = save_response_to_markdown(question, response, root_path)
    print(f"Response saved to {result_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--question", type=str, default="", required=True, help="a question about the Java code, for example 'Tell me about the package structure of the project'")
    parser.add_argument("--max-rounds", type=int, default=20, required=False, help="default 8, maximum rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()
    # the order of the following imports is important
    # since the initialization of langfuse depends on the os environment variables
    # which are loaded in the config_utils module
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager, ResponseManager
    from llm_interaction import process_llm_response, initiate_llm_query_manager, search_results_to_prompt


    # if args.project_root is relative path, then get the absolute path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)
    pf = ProjectFiles(repo_root_path=root_path, prefix_list=["src/main/java"], suffix_list=[".java"])
    # load the files and package gists from persistence.
    pf.from_gist_files()

    question = args.question
    # one of task or jira should be provided
    if not question:
        print("Please provide either question")
        sys.exit(1)
   
    break_down_and_answer(question, pf, root_path, max_rounds=args.max_rounds)
    print("Conversation with LLM ended")