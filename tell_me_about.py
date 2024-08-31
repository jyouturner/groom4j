from typing import Tuple
import os
import sys
import re
import argparse
import yaml
from projectfiles import ProjectFiles


    

from typing import Union
from functions import get_file, get_package, get_static_notes
from functions import efficient_file_search, read_files, read_packages, read_all_packages, read_from_human
from functions import process_file_request


system_prompt = """
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

"""

instructions = """

<instructions>
Begin your analysis with: "Let's inspect the Java project to answer the question: [restate the question]"

<guidelines>
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure, codebase, and feel free to search and access files.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly.
</guidelines>

If you need more information, use the following formats to request it:

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

After receiving information, analyze it and relate it back to the original question. 

Answer to your requests including search results, file contents and package summaries will be found within 
<Additional Materials>
...
<Additional Materials> tags.

During our conversations, your previous notes will be found within
<Previous research notes> 
...
</Previous research notes>tags.

Conclude your analysis with a clear, concise summary that directly addresses the original question.
</instructions>
"""

reused_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}
"""

user_prompt_template = """

You need to inspect <question>{question}</question>

<Previous research notes>
{notes}
</Previous research notes>

<Additional Materials>
{additional_reading}
</Additional Materials>

{instructions}
"""

def ask_continue(query_manager, question, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    additional_reading, processed_requests = process_llm_response(last_response, pf)
    
    if last_response == "" or additional_reading:
        user_prompt = user_prompt_template.format(
            question=question,
            notes=last_response,
            additional_reading="Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading,
            instructions=instructions
        )
        response = query_manager.query(user_prompt)
        return response, additional_reading, False
    else:
        print("The LLM does not need any more information, so we can end the conversation")
        return last_response, None, True
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--question", type=str, default="", required=True, help="a question about the Java code, for example 'Tell me about the package structure of the project'")
    parser.add_argument("--max-rounds", type=int, default=8, required=False, help="default 8, maximum rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()
    # the order of the following imports is important
    # since the initialization of langfuse depends on the os environment variables
    # which are loaded in the config_utils module
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager, ResponseManager
    from llm_interaction import process_llm_response, initiate_llm_query_manager


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
   
    # first let's rewrite the question to be more detailed
    from rewrite_question import expand_question
    from rewrite_question import system_prompt_rewrite_question
    query_manager = initiate_llm_query_manager(pf=None, system_prompt=system_prompt_rewrite_question, reused_prompt_template=None)
    expanded_question = expand_question(query_manager, question)
    
    max_rounds = args.max_rounds
    print(f"question: {expanded_question} max_rounds: {max_rounds}")
    # looping until the user is confident of the steps and instructions, or 8 rounds of conversation
    i = 0
    past_additional_reading = ""
    doneNow = False
    additional_reading = ""
    ResponseManager.reset_prompt_response()
    
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template)
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager, expanded_question, last_response, pf, past_additional_reading=past_additional_reading)
        #print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1
    print("Conversation with LLM ended")