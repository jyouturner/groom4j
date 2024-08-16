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
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

Begin your analysis with: "Let's investigate the Java project to answer the question: [restate the question]"

As you analyze, follow these guidelines:
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure, codebase, and feel free to search and access files.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly and suggest ways to find the information.

If you need more information, use the following formats to request it:

1. To search for keywords:
   [I need to search for keywords: <keyword>keyword1</keyword>, <keyword>keyword2</keyword>]

2. To request file contents:
   [I need content of files:: <file>file1.java</file>, <file>file2.java</file>]

3. To get information about packages:
   [I need info about packages:: <package>com.example.package1</package>, <package>com.example.package2</package>]

Always use these exact formats for requests. After receiving information, analyze it and relate it back to the original question. If you need clarification on any information received, ask for it specifically.

Remember to consider:
- Project structure and architecture
- Relevant design patterns
- Framework-specific configurations
- Potential performance implications
- Security considerations
- Best practices and any deviations from them

Conclude your analysis with a clear, concise summary that directly addresses the original question.
"""
user_prompt_template = """

The ask is <question>{question}</question>

Below is the Java project structure for your reference:
{project_tree}



Previous research notes:
{notes}

Additional reading:
{additional_reading}


"""

query_manager = LLMQueryManager(system_prompt=system_prompt)

def ask_continue(question, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    projectTree = pf.to_tree()
    additional_reading = ""
    for line in last_response.split("\n"):
        # clean line
        line = line.strip()
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
            
        user_prompt = user_prompt_template.format(question = question, project_tree = projectTree, notes = last_response, additional_reading = "Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
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
    parser.add_argument("--question", type=str, default="", required=True, help="a question about the Java code, for example 'Tell me about the package structure of the project'")
    parser.add_argument("--max-rounds", type=int, default=8, required= False, help="default 8, maximam rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()

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
        print("Please provide either question or jira")
        sys.exit(1)
   
    max_rounds = args.max_rounds
    print(f"question: {question} max_rounds: {max_rounds}")
    # looping until the user is confident of the steps and instructions, or 8 rounds of conversation
    i = 0
    past_additional_reading = ""
    doneNow = False
    additional_reading = ""
    ResponseManager.reset_prompt_response()
    
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(question, last_response, pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1

