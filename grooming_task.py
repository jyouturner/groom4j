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

system_prompt = """
You are a world-class Java developer tasked with grooming development tasks in Java projects. Your goal is to write clear, concise, and specific steps to accomplish tasks, focusing only on development aspects (not testing, deployment, or other tasks). Follow this structured approach:

1. Analyze the task:
 - Identify the main components or classes that will be affected
 - Determine if new classes or methods need to be created
 - Consider any potential impacts on existing functionality

2. Research the codebase:
 - If you need to examine specific files, request them like this:
 [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
 - If you need information about packages, ask like this:
 [I need info about packages: <package>package name</package>,<package>package2 name</package>]
 - If you need to search for specific information within the project, use below format:
 [I need to search <keyword>keyword</keyword> in the project]
 - For any other clarifications, use this format:
 [I need clarification about <ask>what you need clarification about</ask>]

3. Plan the implementation:
 - Break down the task into logical steps
 - Consider the order of operations and any dependencies between steps
 - Think about potential edge cases or error scenarios

4. Write the steps:
 - Only write the steps when you are confident in your approach
 - Use this format:
 [Step 1: Brief description]
 [Step 2: Brief description]
 ...
 - Be as specific as possible, mentioning exact file names, method names, or class names where applicable
 - Include any necessary code modifications or additions
 - Provide coding snippets, examples, or best practices to follow when applicable

5. Review and refine:
 - After writing the steps, review them for completeness and clarity
 - Ensure that each step is actionable and specific
 - Consider any potential challenges or risks associated with each step

Remember:
- You are new to this project, so don't hesitate to ask for more information if needed
- Explain your reasoning when requesting additional information
- Begin your analysis with: "Let's break down the task and plan our approach."

"""

user_prompt_template = """
The task to be groomed is:
"{task}"

Below is the Java project structure for your reference:
{project_tree}

Previous research notes:
{notes}

Additional reading:
{additional_reading}

Please analyze this task and provide a detailed plan following the structured approach outlined in your instructions.

"""

query_manager = LLMQueryManager()

def read_files(pf, file_names) -> str:
    additional_reading = ""
    for file_name in file_names:
        file_name = file_name.strip()
        filename,filesummary, filepath, filecontent = get_file(pf, file_name, package=None)
       
        if filename:
            additional_reading += f"<file name=\"{filename}\">\n"
            additional_reading += f"<summary>{filesummary}</summary>\n"
            additional_reading += f"<content>{filecontent}</content></file>\n"
        else:
            additional_reading += f"!!!File {file_name} does not exist! Please ask for the correct file or packages! I am very disappointed!\n"
    return additional_reading


def read_packages(pf, package_names) -> str:
    additional_reading = ""
    for package_name in package_names:
        # clean it
        package_name = package_name.strip()
        packagename, packagenotes, subpackages, filenames = get_package(pf, package_name)
        if packagename:
            additional_reading += f"<package name=\"{packagename}\">\n"
            additional_reading += f"<notes>{packagenotes}</notes>\n"
            additional_reading += f"<sub_packages>{subpackages}</sub_package>\n"
            additional_reading += f"<files>{filenames}</files>\n"
            additional_reading += f"</package>\n"
    return additional_reading

def read_all_packages(pf) -> str:
    additional_reading = ""
    for package in pf.package_notes:
        additional_reading += f"<package name=\"{package}\"><notes>{pf.package_notes[package]}</notes></package>\n"
    return additional_reading

def read_from_human(line) -> str:
    # ask user to enter manually through commmand line
    human_response = input("Please enter the additional reading for the LLM\n")
    additional_reading = f"{human_response}"
    return additional_reading

def search_files_with_keyword(root_path, keyword):
    # search for files with the keyword within the project
    # return the list of file names
    print(f"Searching for files with the keyword: {keyword} under {root_path}")
    matching_files = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith(".java") or file.endswith(".json"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    for line in f:
                        if keyword in line:
                            matching_files.append(file)
                            print(f"Found {keyword} in file: {file_path}")
                            break  # Stop reading the file once the keyword is found
    return matching_files

def ask_continue(task, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
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
            
        user_prompt = user_prompt_template.format(task = task, project_tree = projectTree, notes = last_response, additional_reading = "Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
        # request user click any key to continue
        # input("Press Enter to continue to send message to LLM ...")
        response = query_manager.query(system_prompt, user_prompt)
        return response, additional_reading, False
    else:
        print("the LLM does not need any more information, so we can end the conversation")
        return last_response, None, True
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grooming development task")
    parser.add_argument("--project_root", type=str, default="", required= True, help="absolute path to the project root")
    parser.add_argument("--task", type=str, default="", required=False, help="development task, for example 'Add a health check endpoint to the web service'")
    parser.add_argument("--jira", type=str, default="", required= False, help="URL of the Jira ticket")
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

    task = args.task
    jira = args.jira
    # one of task or jira should be provided
    if not task and not jira:
        print("Please provide either task or jira")
        sys.exit(1)
    # if jira is provided, then get the task from Jira
    if jira:
        from my_jira import MyJira
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
    
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(task, last_response, pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1

