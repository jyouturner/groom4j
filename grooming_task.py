from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles

from typing import Union, Optional
from functions import get_file, get_package, get_static_notes, efficient_file_search, process_file_request
from functions import read_files, read_packages, read_all_packages, read_from_human, save_response_to_markdown
from functions import function_prompt
import logging

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()

from llm_client import LLMQueryManager, langfuse_context, observe
from conversation_reviewer import ConversationReviewer
from llm_interaction import initiate_llm_query_manager, query_llm
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

system_prompt = """
You are a world-class Java developer tasked with grooming development tasks in Java projects. Your goal is to write clear, concise, and specific steps to accomplish tasks, focusing only on development aspects (not testing, deployment, or other tasks).
"""

instructions = """

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

Important: When you identify key findings, present them in the following format:

KEY_FINDINGS:
- [BUSINESS_RULE] Description of a business rule
- [IMPLEMENTATION_DETAIL] Description of an important implementation detail
- [DATA_FLOW] Description of a significant aspect of the data flow
- [ARCHITECTURE] Description of a notable architectural decision
- [SPECIAL_CASE] Description of any special cases or exceptions

Ensure that each key finding starts with the appropriate tag in square brackets.


Remember:
- Explain your reasoning when requesting additional information
- Begin your analysis with the Task Analysis section, then proceed with "Let's break down the task and plan our approach."

"""



reused_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}

and notes of the files in the project:
{file_notes}
"""

user_prompt_template = """
===CONVERSATION_CONTEXT===
Iteration: {iteration_number}

===MAIN TASK===
{question}

===KEY_FINDINGS===
{key_findings}

===PREVIOUS_ANALYSIS===
{previous_llm_response}


===NEW_INFORMATION===

{new_information}


===INSTRUCTIONS_FOR_ADDITIONAL_REQUESTS===
{function_prompt}

===DO_NOT_SEARCH===
{do_not}

===GUIDELINES_FOR_ANALYSIS===
{instructions}

"""

final_user_prompt_template = """
===MAIN TASK===
{question}

===KEY_FINDINGS===
{key_findings}

===PREVIOUS_ANALYSIS===
{previous_llm_response}


===NEW_INFORMATION===

{new_information}

===GUIDELINES_FOR_ANALYSIS===
{instructions}
"""

@observe(name="grooming_task", capture_input=True, capture_output=True)
def grooming_task(pf: Optional[ProjectFiles], task, last_response="", max_rounds=8):
    """
    Given a task, groom it by interacting with the LLM.
    Args:
    pf: The ProjectFiles object.
    task (str): The task to be groomed.
    max_rounds (int): The maximum number of rounds of conversation with LLM before stopping the conversation.
    """
    logger.info(f"Task: {task}")
    logger.info(f"Max rounds: {max_rounds}")
    i = 0
    new_information = ""
    key_findings = []

    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier1")
    query_manager_tier2 = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier2")
    reviewer = ConversationReviewer(query_manager=query_manager_tier2)
    final_answer_prompt = None
    while i < max_rounds:
        logger.info(f"--------- Round {i} ---------")
        try:
            new_information, last_response, should_conclude, key_findings = query_llm(
                query_manager, question=task, user_prompt_template=user_prompt_template,
                instruction_prompt=instructions, function_prompt=function_prompt, last_response=last_response,
                pf=pf, 
                iteration_number=str(i),
                new_information=new_information,
                key_findings=key_findings,
                reviewer=reviewer
            )
            if should_conclude:
                logger.info("The conversation is about to end")
                if final_answer_prompt:
                    logger.info("but we still need to do the final conversation...")
                    _, last_response, _, _, _ = query_llm(query_manager=query_manager, question=task, user_prompt_template=final_user_prompt_template,
                              instruction_prompt=final_answer_prompt, function_prompt="", last_response=last_response, pf=pf,
                              iteration_number=str(i), new_information=new_information, key_findings=key_findings, reviewer=None)
                break
        except Exception as e:
            logger.error(f"An error occurred in round {i}: {str(e)}", exc_info=True)
            raise
        i += 1
    logger.info(f"Total rounds: {i}")
    return last_response


        
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
        from integration import MyJira
        myJira = MyJira(host=os.environ.get("JIRA_SERVER"), user=os.environ.get("JIRA_USERNAME"), api_token=os.environ.get("JIRA_API_TOKEN"))
        issue = myJira.find_issue(jira)
        task = issue.fields.description
    max_rounds = args.max_rounds
    print(f"Task: {task} max_rounds: {max_rounds}")
    response = grooming_task(pf, task, last_response="", max_rounds=args.max_rounds)
    logger.info(response)
    print("Conversation with LLM ended")

    # save to a gist file
    result_file = save_response_to_markdown(task, response, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")
