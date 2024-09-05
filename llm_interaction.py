import re
import os
from typing import List, Tuple, Optional
from projectfiles import ProjectFiles
from functions import efficient_file_search, read_files, read_packages, process_file_request, get_static_notes
from llm_client import LLMQueryManager, langfuse_context
from conversation_reviewer import ConversationReviewer
import logging
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# the global search results dict with key being the search keyword, the value being a list of file names, or [] if no matching files
# this is important to avoid repeated search for the same keyword
global_search_results = {}

function_prompt = """
If you need more information, use the following formats to request it:

1. To search for keywords:
   [I need to search for keywords: <keyword>keyword1</keyword>, <keyword>keyword2</keyword>]
   I will provide the results in this format:
   ```text
   You requested to search for : [keyword]
   Here are the results:<files><file>file1.java</file>, <file>file2.java</file></files>
   ```
   Or if no files are found:
   ```text
   No matching files found with [keyword]
   ```

2. To request file contents:
   [I need content of files: <file>file1.java</file>, <file>file2.java</file>]
   I will provide a summary and content of the file, or notify you if the file is not found.

3. To get information about packages:
   [I need info about packages:: <package>com.example.package1</package>, <package>com.example.package2</package>]
   I will provide a summary of the package and its files.

Make your requests for additional information at the end of your response, using this format:

**Next Steps**
[your request to search for keywords]
[your request to read files]
[your request to read packages]
...

You can include multiple requests in the Next Steps section. Be selective and efficient in your requests, focusing on information most relevant to the task at hand.

After receiving the requested information, analyze it and relate it back to the original question. The answers to your requests, including search results, file contents, and package summaries, will be provided in the NEW_INFORMATION section of the next prompt.
"""

do_not_search_prompt = """
The following terms have already been searched and confirmed not to exist in the project:
[{not_found_terms}]

"""

def not_found_terms(search_results: dict = None) -> str:
    # print the search results in the format that can be used in the LLM prompt
    # keyword: [file1, file2]
    # or
    # keyword: not found in project
    if not search_results:
        search_results = global_search_results
    result_str = ""
    for keyword, files in search_results.items():
        if not files:
            result_str += f"\n{keyword}"
    return result_str

def initiate_llm_query_manager(pf: Optional[ProjectFiles], system_prompt, reused_prompt_template):
    use_llm = os.environ.get("LLM_USE")
    # prompts can be reused and cached in the LLM if it is supported
    if pf is not None:
        package_notes = get_static_notes(pf)
        project_tree = pf.to_tree()
        file_notes = pf.get_file_notes()
    else:
        project_tree = ""
        package_notes = ""
        file_notes = ""
    if reused_prompt_template is not None:
        cached_prompt = reused_prompt_template.format(project_tree=project_tree, 
        package_notes=package_notes, file_notes=file_notes)
    else:
        cached_prompt = None
    query_manager = LLMQueryManager(use_llm=use_llm, system_prompt=system_prompt, cached_prompt=cached_prompt)
    
    return query_manager


def process_llm_response(response: str, pf: ProjectFiles) -> Tuple[str, str, bool]:
    """
    
    return new_information, response, stop_function_prompt
    """
    new_information = ""
    stop_function_prompt = False
    next_steps_index = response.find("**Next Steps**")
    if next_steps_index == -1:
        logger.info("No next steps found in the response")
        return new_information, response, stop_function_prompt

    next_steps = response[next_steps_index:].strip()
    if not next_steps:
        logger.info("process_llm_response: No next steps found in the response")
        return new_information, response, stop_function_prompt

    logger.debug(f"Next steps: {next_steps}")
    lines = next_steps.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "[I need to search" in line:
            keywords = re.findall(r'<keyword>(.*?)</keyword>', line)
            for keyword in keywords:
                logger.info(f"LLM needs to search: {keyword}")
                
                matching_files = []
                if keyword in global_search_results:
                    matching_files = global_search_results[keyword]
                else:
                    # Perform the actual search, with all the common extensions
                    matching_files = efficient_file_search(pf.root_path, keyword, file_extensions=[".java", ".xml", ".yml", ".yaml", ".properties", ".sql", ".json"])           
                    # remember the search results so we don't have to search again
                    global_search_results[keyword] = matching_files
                logger.info(f"Found matching files: {matching_files} for keyword: {keyword}")
                if matching_files: 
                    files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                    new_information += f"\nYou requested to search for '{keyword}'\nHere are results: {files_str}\n"
                else:
                    new_information += f"\nNo matching files found with '{keyword}'\n"
                    

        elif "[I need content of files:" in line or "[I need access files:" in line:
            file_names = process_file_request(lines[i:])
            request = f"{', '.join(file_names)}"
            file_contents, files_found, files_not_found = read_files(pf, file_names)
            new_information += file_contents
            logger.info(f"files_found: {files_found}" )
            logger.info(f"files_not_found: {files_not_found}")

        elif "[I need info about packages:" in line:
            pattern = r'<package>(.*?)</package>'
            package_names = re.findall(pattern, line)
            package_contents, packages_found, packages_not_found = read_packages(pf, package_names)
            new_information += package_contents
            logger.info(f"packages_found: {packages_found}" )
            logger.info(f"packages_not_found: {packages_not_found}")

        i += 1


    # Remove the **Next Steps** section and everything following it
    updated_response = response[:next_steps_index].strip()

    return new_information, updated_response, stop_function_prompt


def query_llm(query_manager, question, user_prompt_template, instruction_prompt, last_response, pf, iteration_number: str="", new_information: str="", stop_function_prompt: bool=False, reviewer: ConversationReviewer=None) -> Tuple[str, str, bool]:
    """
    return new_information, response, stop_function_prompt
    """
    user_prompt = user_prompt_template.format(
        iteration_number=iteration_number,
        question=question,
        previous_llm_response=last_response,
        do_not=do_not_search_prompt.format(not_found_terms=not_found_terms()),
        new_information=str(new_information) if new_information else "",
        instructions=instruction_prompt,
        function_prompt=function_prompt if not stop_function_prompt else "",
    )
    response = query_manager.query(user_prompt)
    # update the tracing with the iteration number
    langfuse_context.update_current_observation(tags=[iteration_number])
    
    if reviewer is not None:
        # Add the conversation to the reviewer's history
        if iteration_number != "0":
            reviewer.add_conversation(new_information, response)
        else:
            reviewer.add_conversation(question, response)
        
        # Only review every 3 rounds
        if int(iteration_number) % 3 == 0:
            should_continue = reviewer.should_continue_conversation()
            if not should_continue:
                logger.info("The conversation reviewer does not want to continue the conversation")
                # make sure to remove anything that after the **Next Steps** section
                next_steps_index = response.find("**Next Steps**")
                if next_steps_index != -1:
                    response = response[:next_steps_index]
                return None, response, True

    # process the LLM response, and get the new information, the updated response, and whether the function prompt should be stopped
    try:
        new_information, response, stop_function_prompt = process_llm_response(response, pf)
    except Exception as e:
        logger.error(f"An error occurred in processing LLM response: {str(e)}", exc_info=True)
        return None, response, True
    
    return new_information, response, stop_function_prompt
