from typing import Tuple
import os
import sys
import re
import argparse
import yaml
from projectfiles import ProjectFiles
import time
from typing import Union, Optional, List
from functions import get_file, get_package, get_static_notes
from functions import efficient_file_search, read_files, read_packages, read_all_packages, read_from_human
from functions import process_file_request
from functions import save_response_to_markdown

import logging

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()

from rewrite_question import decompose_question, system_prompt_rewrite_question

from llm_client import LLMQueryManager, langfuse_context, observe
from conversation_reviewer import ConversationReviewer
from llm_interaction import initiate_llm_query_manager, query_llm
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

system_prompt = """
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. Your task is to investigate a specific question about the Java codebase.

"""

instructions = """
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure and codebase.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly.
5. The goal is to be as thorough as possible to help developers plan for maintenance tasks more effectively.

6. Synthesize information as you go:
   - After each round, summarize what you've learned so far.
   - Connect new information with previous findings.
   - Highlight any changes to your understanding based on new information.

7. Provide partial answers or hypotheses:
   - Even with incomplete information, offer your best current understanding.
   - Clearly label any hypotheses or assumptions you're making.
   - Update or revise your partial answers as you gather more information.

8. Assess information sufficiency:
   - At the end of each response, evaluate whether you have enough information to fully answer the question.
   - If you believe you have sufficient information, state so explicitly and provide your final answer.
   - If you need more information, clearly state what specific information you need and why.

9. Avoid repetitive requests:
   - Before requesting information, check if it's already been provided in previous rounds.
   - If you're unsure about previously provided information, ask for clarification rather than requesting the same information again.

   Remember to integrate both new information and previously identified important points in your analysis.

Important: When you identify key findings, present them in the following format:

KEY_FINDINGS:
- [BUSINESS_RULE] Description of a business rule
- [IMPLEMENTATION_DETAIL] Description of an important implementation detail
- [DATA_FLOW] Description of a significant aspect of the data flow
- [ARCHITECTURE] Description of a notable architectural decision
- [SPECIAL_CASE] Description of any special cases or exceptions

Ensure that each key finding starts with the appropriate tag in square brackets.

Remember, the goal is to provide the most comprehensive and accurate answer possible. It's okay to revise your understanding as you gather more information, and it's better to provide a well-reasoned partial answer than to continue requesting information indefinitely.

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

===QUESTION===
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





@observe(name="answer_question", capture_input=True, capture_output=True)
def answer_question(pf: Optional[ProjectFiles], question, last_response="", max_rounds=8):
    """
    Given a question, answer it by interacting with the LLM.
    Args:
    pf: The ProjectFiles object.
    question (str): The question to be answered.
    max_rounds (int): The maximum number of rounds of conversation with LLM before stopping the conversation.
    """
    logger.info(f"Answer question: {question}")
    logger.info(f"Max rounds: {max_rounds}")
    i = 0
    new_information = ""
    key_findings = []
    # initiate the LLM query manager
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier1")
    query_manager_tier2 = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier2")
    reviewer = ConversationReviewer(query_manager=query_manager_tier2)
    while i < max_rounds:
        logger.info(f"--------- Round {i} ---------")
        try:
            new_information, last_response, should_conclude, key_findings = query_llm(
                query_manager, question=question, user_prompt_template=user_prompt_template,
                instruction_prompt=instructions, last_response=last_response,
                pf=pf, 
                iteration_number=str(i),
                new_information=new_information,
                key_findings=key_findings,
                reviewer=reviewer
            )
            if should_conclude:
                logger.info("The conversation has ended or no new information was found")
                break
        except Exception as e:
            logger.error(f"An error occurred in round {i}: {str(e)}", exc_info=True)
            raise
        i += 1
    logger.info(f"Total rounds: {i}")
    # get the total tokens from langfuse
    total_tokens = query_manager.get_total_tokens()
    logger.info(f"Total tokens: {total_tokens}")
    return last_response



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
        logger.info(f"Question: {q}")
        response = answer_question(pf, q, last_response="", max_rounds=max_rounds)
        logger.info(response)
        research_notes += f"\n\n===Question: {q}===\n\n{response}"
        # Write to a markdown file, in root_path/.gist/tell_me_about/
        result_file = save_response_to_markdown(q, response, path=root_path+"/.gist/tell_me_about/")
        logger.info(f"Response saved to {result_file}")

    # Now let's answer the refined question with answers to the decomposed questions
    response = answer_question(pf, refined_question, last_response=research_notes, max_rounds=args.max_rounds)
    # Save to markdown file
    result_file = save_response_to_markdown(question, response, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")
    return response




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--question", type=str, default="", required=True, help="a question about the Java code, for example 'Tell me about the package structure of the project'")
    parser.add_argument("--max-rounds", type=int, default=8, required=False, help="default 8, maximum rounds of conversation with LLM before stopping the conversation")
    parser.add_argument("--breakdown", type=bool, default=False, required=False, help="bool indicator whether to break down the question into smaller questions")
    args = parser.parse_args()



    # if args.project_root is relative path, then get the absolute path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        logger.error(f"Error: {root_path} does not exist")
        sys.exit(1)
    pf = ProjectFiles(repo_root_path=root_path)
    # load the files and package gists from persistence.
    pf.from_gist_files()

    question = args.question
    # one of task or jira should be provided
    if not question:
        logger.error("Please provide a question")
        sys.exit(1)
    if bool(args.breakdown):
        logger.info("Breaking down the question into smaller questions ...")
        res = break_down_and_answer(question, pf, root_path, max_rounds=args.max_rounds)
        logger.info(res)
    else:
        res = answer_question(pf, question, max_rounds=args.max_rounds)
        logger.info(res)
        # Write to a markdown file
        result_file = save_response_to_markdown(question, res, path=root_path+"/.gist/tell_me_about/")
        logger.info(f"Response saved to {result_file}")
    logger.info("Conversation with LLM ended")