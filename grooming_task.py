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
from functions import get_file, get_package, get_static_notes
from functions import search_files_with_keyword, read_files, read_packages, read_all_packages, read_from_human
from gist_api import default_api_notes_file

system_prompt = """
You are a world-class Java developer tasked with grooming development tasks in Java projects. Your goal is to write clear, concise, and specific steps to accomplish tasks, focusing only on development aspects (not testing, deployment, or other tasks). Follow this structured approach:

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
 - If you need to examine specific files, request them in this format:
 [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
 - If you need information about packages, ask in this format:
 [I need info about packages: <package>package name</package>,<package>package2 name</package>]
 - If you need to search for specific information within the project, use below format:
 [I need to search <keyword>keyword</keyword> in the project]

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
 - If you have questions that you can not find answer by researching the codebase, you can leave them at the end of the steps. In a section named "Questions".

5. Review and refine:
 - After writing the steps, review them for completeness and clarity
 - Ensure that each step is actionable and specific
 - Consider any potential challenges or risks associated with each step

Remember:
- Explain your reasoning when requesting additional information
- Begin your analysis with the Task Analysis section, then proceed with "Let's break down the task and plan our approach."
"""

reused_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}
"""

user_prompt_template = """
The task to be groomed is:
"{task}"

Previous research notes:
{notes}

Additional reading:
{additional_reading}

Please perform a Task Analysis following the structured approach outlined in your instructions, then proceed with analyzing this task and providing a detailed plan.
"""


def initiate_llm_query_manager(pf):
    use_llm = os.environ.get("USE_LLM")
    # prompts can be reused and cached in the LLM if it is supported
    package_notes = get_static_notes(pf)
    project_tree = pf.to_tree()
    cached_prompt = reused_prompt_template.format(project_tree=project_tree, package_notes=package_notes)
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager

def ask_continue(query_manager, task, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
    projectTree = pf.to_tree()
    
    additional_reading = ""

    if last_response == "":
        # Initial conversation: perform Task Analysis
        user_prompt = user_prompt_template.format(task=task, project_tree=projectTree, notes="", additional_reading="")
        response = query_manager.query(user_prompt)
        
        # Extract Task Analysis results
        task_analysis = extract_task_analysis(response)
        
        # Use Task Analysis to guide further research
        additional_reading = perform_guided_research(task_analysis, pf)
        
        return response, additional_reading, False
    
    for line in last_response.split("\n"):
        # clean line
        line = line.strip()
        if line.startswith("[I need to search"):
            # [I need to search <search>what you need to search</search>]
            match = re.search(r'<keyword>(.*?)</keyword>', line)
            if match:
                what = match.group(1)
                print(f"LLM needs to search: {what}")
                # search for files with the keyword within the project
                files = search_files_with_keyword(pf.root_path, what)
                for file in files:
                    additional_reading += f"Found {what} in file: {file}\n"
                additional_reading += f"Found {len(files)} files with the keyword: {what}\n "
        elif line.startswith("[I need content of files:") or line.startswith("[I need access files:"):
            # example [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
            # LLM needs access to files: ['com/homedepot/fbr/response/Item.java', 'com/homedepot/fbr/service/FBRResource.java']
            # Define a regex pattern to match content between <file> and </file> tags
            pattern = r'<file>(.*?)</file>'
            file_names = re.findall(pattern, line)
            print(f"LLM needs access to files: {file_names}")
            additional_reading += read_files(pf, file_names)
            print(f"contents provided for {file_names}")            
        elif line.startswith("[I need info about packages:"):
            # [I need info about packages: <package>package name</package>,<package>package2 name</package>,<package>package3 name</package>]
            # Need more info of package: ['com.fasterxml.jackson.databind']
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
    if additional_reading:
        user_prompt = user_prompt_template.format(task=task, project_tree=projectTree, notes=last_response, additional_reading="Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
        response = query_manager.query(user_prompt)
        return response, additional_reading, False
    else:
        print("The LLM does not need any more information, so we can end the conversation")
        return last_response, None, True

def extract_task_analysis(response):
    # Extract Task Analysis results from the LLM's response
    # This is a simple implementation; you might want to use regex for more robust extraction
    task_analysis = {
        'summary': '',
        'metrics_issues': [],
        'investigation_points': [],
        'assumptions': []
    }
    
    lines = response.split('\n')
    current_section = None
    
    for line in lines:
        if line.startswith('[Task Summary:'):
            current_section = 'summary'
            task_analysis['summary'] = line.split(':', 1)[1].strip()
        elif line.startswith('[Key Metrics/Issues:'):
            current_section = 'metrics_issues'
        elif line.startswith('[Investigation Points:'):
            current_section = 'investigation_points'
        elif line.startswith('[Assumptions/Potential Misunderstandings:'):
            current_section = 'assumptions'
        elif line.strip().startswith('-') or line.strip().startswith('1.'):
            if current_section in ['metrics_issues', 'investigation_points', 'assumptions']:
                task_analysis[current_section].append(line.strip()[2:].strip())
    
    return task_analysis

def perform_guided_research(task_analysis, pf):
    additional_reading = ""
    
    # Use investigation points to guide research
    for point in task_analysis['investigation_points']:
        # Search for keywords related to the investigation point
        keywords = extract_keywords(point)
        for keyword in keywords:
            files = search_files_with_keyword(pf.root_path, keyword)
            for file in files:
                additional_reading += f"Found {keyword} in file: {file}\n"
            additional_reading += f"Found {len(files)} files with the keyword: {keyword}\n"
    
    # Add any other guided research based on the task analysis
    
    return additional_reading

def extract_keywords(text):
    # Simple keyword extraction (you might want to use NLP techniques for better results)
    return [word.lower() for word in text.split() if len(word) > 3]
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grooming development task")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--task", type=str, default="", help="Development task, for example 'Add a health check endpoint to the web service'")
    parser.add_argument("--jira", type=str, default="", help="URL of the Jira ticket")
    parser.add_argument("--max-rounds", type=int, default=8, help="Maximum rounds of conversation with LLM before stopping the conversation (default: 8)")
    args = parser.parse_args()
    print(args)
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
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf)
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager, task, last_response, pf, past_additional_reading=past_additional_reading)
        print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1

