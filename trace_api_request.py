# trace_api_request.py
# This is similar to tell_me_about.py, but it is specifically for API requests.






from typing import Tuple, Union, Optional, List
import os
import sys
import argparse
import logging
from projectfiles import ProjectFiles
from functions import save_response_to_markdown
from config_utils import load_config_to_env
load_config_to_env()

from llm_client import LLMQueryManager, langfuse_context, observe
from conversation_reviewer import ConversationReviewer
from llm_interaction import initiate_llm_query_manager, query_llm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

system_prompt = """
You are an AI assistant specialized in analyzing Java applications. Your role is to help engineers understand the flow of data and business logic in these applications. 
"""

instructions = """
1. Analyze the provided code thoroughly.
2. Explain the data flow step-by-step, from the HTTP request to the response.
3. Highlight any special business logic or notable implementation details.
4. If relevant, describe the structure of the data being returned.
5. Keep your explanations clear and concise, suitable for experienced developers.
6. If you're unsure about something, state it clearly.
7. Provide partial answers or hypotheses when information is incomplete.
8. Assess information sufficiency and request specific additional information if needed.

Always base your answers on the provided code and information. If there's ambiguity or missing information, state your assumptions clearly.

IMPORTANT: Maintain consistency throughout the conversation. If you identify any key points, including special business rules or important details, make sure to include them in all relevant parts of your analysis, including the final response structure.

"""

reused_prompt_template = """
Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}

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

Remember to integrate both new information and previously identified important points in your analysis.

When you identify key findings, present them in the following format:

**KEY_FINDINGS**:
- [BUSINESS_RULE] Description of a business rule
- [IMPLEMENTATION_DETAIL] Description of an important implementation detail
- [DATA_FLOW] Description of a significant aspect of the data flow
- [ARCHITECTURE] Description of a notable architectural decision
- [SPECIAL_CASE] Description of any special cases or exceptions

Ensure that each key finding starts with a hyphen followed by a space and the appropriate tag in square brackets, exactly as shown above. Do not use asterisks or other formatting within the key findings list.
"""

trace_api_question_prompt = """
Given a API request: {api_request}

1. Trace the request through the code, and find out the step-by-step flow of data and logic from receiving the request to sending the response.
2. What is the response data for this request?
3. Are there any special business rules or implementation details that are worth noting?

"""

@observe(name="trace_api_request", capture_input=True, capture_output=True)
def trace_api_request(pf: Optional[ProjectFiles], api_request, last_response="", max_rounds=8):
    logger.info(f"Tracing API request: {api_request}")
    logger.info(f"Max rounds: {max_rounds}")
    i = 0
    new_information = ""
    key_findings = []
    
    query_manager = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier1")
    query_manager_tier2 = initiate_llm_query_manager(pf, system_prompt, reused_prompt_template, tier="tier2")
    reviewer = ConversationReviewer(query_manager=query_manager_tier2)

    # create the question from the api_request
    question = trace_api_question_prompt.format(api_request=api_request)
    
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
    total_tokens = query_manager.get_total_tokens()
    logger.info(f"Total tokens: {total_tokens}")
    return last_response

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trace API Request")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--api-request", type=str, required=True, help="The API request to trace, e.g., 'GET /api/v1/city/{cityName}'")
    parser.add_argument("--max-rounds", type=int, default=8, required=False, help="Maximum rounds of conversation with LLM before stopping")
    args = parser.parse_args()

    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        logger.error(f"Error: {root_path} does not exist")
        sys.exit(1)
    
    pf = ProjectFiles(repo_root_path=root_path)
    pf.from_gist_files()

    api_request = args.api_request
    if not api_request:
        logger.error("Please provide an API request to trace")
        sys.exit(1)

    res = trace_api_request(pf, api_request, max_rounds=args.max_rounds)
    logger.info(res)
    
    result_file = save_response_to_markdown(f"endpoint{api_request}", res, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")
    logger.info("API request tracing completed")