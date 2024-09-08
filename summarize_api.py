from typing import Tuple
import os
import sys
import re
import argparse
from projectfiles import ProjectFiles

from typing import Union, Optional
from functions import get_file, get_package, efficient_file_search, process_file_request, get_static_notes
from functions import read_files, read_packages, read_all_packages, read_from_human
from functions import save_response_to_markdown
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
You are an AI assistant designed to help Java developers understand existing Java projects.
"""

instructions = """
If you encounter unclear or complex code, state your assumptions and any potential alternative interpretations. Always err on the side of providing more detail, especially when it comes to data flow analysis.

Prioritize thoroughness over speed. If the project is large, focus on the most important or frequently used endpoints first, but ensure that the data flow analysis for each endpoint is as complete as possible.

You must follow exactly the above specified format for requests and structure your response using markdown.

Important: When you identify key findings, present them in the following format:

KEY_FINDINGS:
- [BUSINESS_RULE] Description of a business rule
- [IMPLEMENTATION_DETAIL] Description of an important implementation detail
- [DATA_FLOW] Description of a significant aspect of the data flow
- [ARCHITECTURE] Description of a notable architectural decision
- [SPECIAL_CASE] Description of any special cases or exceptions

Ensure that each key finding starts with the appropriate tag in square brackets.

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

# very specific to this script
question = """
Your task is to analyze the project structure, identify API endpoints, and provide detailed notes on their implementation, with a strong focus on data flow analysis.

For each API endpoint you identify, provide the following information in markdown format:

## [Endpoint Name]

1. **Purpose**: Briefly describe the purpose of this endpoint.

2. **Functionality**: Explain what this endpoint does in detail.

3. **Request Structure**:
   - HTTP Method
   - Path parameters
   - Query parameters
   - Request body (if applicable)

4. **Response Structure**:
   - Response body
   - Possible status codes

5. **Data Flow**:
   - For GET requests: 
     - Explain in detail how data is retrieved, including all database queries and external service calls.
     - Trace the data flow from the initial request to the final response, including any intermediate services or caches.
     - Describe any data transformations that occur along the way.
     - If multiple data sources are involved, explain how the data is aggregated or joined.
   - For POST requests: 
     - Describe how data is processed and saved, step by step.
     - Detail all validations and transformations applied to the incoming data.
     - If data is stored in a database, provide details on the schema and any constraints.
     - Explain any cascading effects or triggers that might be activated by the data change.

6. **Data Processing**: 
   - Detail all transformations or business logic applied to the data.
   - Explain any caching mechanisms used and how they affect data retrieval or storage.
   - Describe any asynchronous processing or background jobs triggered by this endpoint.

7. **Key Classes/Methods**: 
   - List the main classes and methods involved in handling this endpoint.
   - For each key method, briefly explain its role in the data flow.

Provide code snippets and file locations where relevant.
"""


@observe(name="summarize_api", capture_input=True, capture_output=True)
def summarize_api(pf: Optional[ProjectFiles], question, last_response="", max_rounds=8):
    """
    Find all the API endpoints in the project and summarize them with the LLM.
    Args:
    pf: The ProjectFiles object.
    question (str): The question to be answered.
    max_rounds (int): The maximum number of rounds of conversation with LLM before stopping the conversation.
    """
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
    return last_response
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--max-rounds", type=int, default=8, required= False, help="default 8, maximam rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()
    # Convert to absolute path if it's a relative path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(repo_root_path=root_path)
    # load the files and package gists from persistence.
    pf.from_gist_files()
   
    max_rounds = args.max_rounds

    response = summarize_api(pf, question, last_response="", max_rounds=args.max_rounds)
    logger.info(response)

    # save to a gist file
    result_file = save_response_to_markdown("api_notes", response, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")