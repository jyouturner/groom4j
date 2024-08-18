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
from functions import efficient_file_search, read_files, read_packages, read_all_packages, read_from_human
from functions import process_file_request

system_prompt = """
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

Begin your analysis with: "Let's inspect the Java project to answer the question: [restate the question]"

As you analyze, follow these guidelines:
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure, codebase, and feel free to search and access files.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly and suggest ways to find the information.

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

Always use these exact formats for requests. After receiving information, analyze it and relate it back to the original question. If you need clarification on any information received, ask for it specifically.

Remember to consider:
- Project structure and architecture
- Relevant design patterns
- Framework-specific configurations

During our conversations, your previous notes will be found within
<Previous research notes> 
...
</Previous research notes>tags, 
and any answer to your requests including search results, file contents and package summaries will be found within 
<Additional Materials>
...
<Additional Materials> tags.

Conclude your analysis with a clear, concise summary that directly addresses the original question.
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


"""

def initiate_llm_query_manager(pf):
    use_llm = os.environ.get("USE_LLM")
    # prompts can be reused and cached in the LLM if it is supported
    package_notes = get_static_notes(pf)
    project_tree = pf.to_tree()
    cached_prompt = reused_prompt_template.format(project_tree=project_tree, package_notes=package_notes)
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager

def ask_continue(query_manager, question, last_response, pf, past_additional_reading) -> Tuple[str, str, bool]:
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
            file_extensions = ['.java', '.yml', '.properties']  # Add or modify as needed
    
            matching_files = efficient_file_search(pf.root_path, what, file_extensions=file_extensions)

            if matching_files:
                files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>{files_str}</files>\n</search>\n"
            else:
                additional_reading += f"<search><keyword>{what}</keyword>\n    <files>No matching files found</files>\n</search>\n"

        elif "[I need content of files:" in line or "[I need access files:" in line:
            # example [I need access files: <file>file1 name</file>,<file>file2 name</file>,<file>file3 name</file>]
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
        #elif "[I need clarification about" in line:
            # [I need clarification about <ask>what you need clarification about</ask>]
        #    what = re.search(r'<ask>(.*?)</ask>', line).group(1)
        #    print(f"LLM needs more information: \n{what}")
            # ask user to enter manually through commmand line
        #    additional_reading += f"Regarding {what}, {read_from_human(line)}\n"
        #elif "[I need" in line:
        #    print(f"LLM needs more information: \n{line}")
        #    additional_reading += f"{read_from_human(line)}\n"
        else:
            pass
        i += 1
    if last_response=="" or additional_reading:
        # either the first time or the last conversation needs more information            
        user_prompt = user_prompt_template.format(question = question, notes = last_response, additional_reading = "Below is the additional reading you asked for:\n" + past_additional_reading + "\n\n" + additional_reading)
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
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf)
    while True and i < max_rounds:
        last_response = ResponseManager.load_last_response()
        response, additional_reading, doneNow = ask_continue(query_manager, question, last_response, pf, past_additional_reading=past_additional_reading)
        #print(response)
        # check if the user is confident of the steps and instructions
        if doneNow:
            print(response)
            break
        else:
            past_additional_reading += ("\n" + additional_reading)
            i += 1
    print("Conversation with LLM ended")
