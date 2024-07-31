from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles
from dotenv import load_dotenv
load_dotenv(override=True)

from llm_router import query, load_the_last_response, reset_prompt_response
from typing import Union
from functions import get_file, get_package

prompt_continue_template = """
You are a world class Java developer, you are grooming a development task in a Java project: 

"{task}"

Below is the Java project structure for your reference:
{project_tree}

You need to write the steps to accomplish the task. For now only focus on development tasks only. Do not focus on testing, deployment, or other tasks.

Since you are new to this project, if you have questions or need help, you are encouraged to ask for help, in below format:
[I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
[I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]

If you need more information, please ask for it in the following format:
[I need clarification about <ask>what you need clarification about</ask>]

Your end goal is to write the steps in a clear and concise manner, for example
[Step 1]
[Step 2]
...

You only write the steps after you are very sure of the steps. If you are not sure, ask for more info of the files or packages and your reasoning.

below are your notes from previous research of the project:
{notes}

{additional_reading}

The steps need to be as specific as possible. 
"""

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

def ask_continue(task, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    projectTree = pf.to_tree()
    additional_reading = ""
    for line in last_response.split("\n"):
        if line.startswith("[I need access files:"):
            # example [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
            # Define a regex pattern to match content between <file> and </file> tags
            pattern = r'<file>(.*?)</file>'
            file_names = re.findall(pattern, line)
            print(f"LLM needs access to files: {file_names}")
            additional_reading += read_files(pf, file_names)            
        elif line.startswith("[I need info about packages:"):
            # [I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]
            pattern = r'<package>(.*?)</package>'
            package_names = re.findall(pattern, line)
            print(f"Need more info of package: {package_names}")
            additional_reading += read_packages(package_names)
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
            
        prompt = prompt_continue_template.format(task = task, project_tree = projectTree, notes = last_response, additional_reading = "Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
        # request user click any key to continue
        # input("Press Enter to continue to send message to LLM ...")
        response = query(prompt)
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
    reset_prompt_response()
    
    while True and i < max_rounds:
        last_response = load_the_last_response()
        response, additional_reading, doneNow = ask_continue(task, last_response, pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1

