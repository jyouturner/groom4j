import re
import os
from typing import List, Tuple, Optional
from projectfiles import ProjectFiles
from functions import efficient_file_search, read_files, read_packages, process_file_request, get_static_notes
from functions import make_api_call, make_db_query
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
   [I need info about packages: <package>com.example.package1</package>, <package>com.example.package2</package>]
   I will provide a summary of the package and its files.

4. To get response data from an external API:
   [I need external API response for: <api>API_NAME</api>, <endpoint>/path/to/endpoint</endpoint>, <params>param1=value1&param2=value2</params>]
   I will provide the response data from the external API for the specified endpoint and parameters.

5. To get results from a database query:
   [I need database query results for: <db>DATABASE_NAME</db>, <query>SELECT * FROM table WHERE condition</query>]
   For SQL databases, provide the SQL query. For NoSQL databases, describe the query in natural language.
   I will provide the results of executing this query on the specified database.

Make your requests for additional information at the end of your response, using this format:

**Next Steps**
[your request to search for keywords]
[your request to read files]
[your request to read packages]
[your request for external API response]
[your request for database query results]
...

You can include multiple requests in the Next Steps section. Be selective and efficient in your requests, focusing on information most relevant to the task at hand.

For external API and database requests:
- Clearly specify the API name or database name.
- For APIs, provide the exact endpoint and any necessary parameters.
- For databases, provide a precise query or description of the data you need.
- Explain why you need this information and how it relates to the current task.

After receiving the requested information, analyze it and relate it back to the original question. The answers to your requests, including search results, file contents, package summaries, API responses, and database query results, will be provided in the NEW_INFORMATION section of the next prompt.
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

def initiate_llm_query_manager(pf: Optional[ProjectFiles], system_prompt, reused_prompt_template, tier="tier1"):
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
    #FIXME: need to add the max_calls, period, max_tokens_per_min, max_tokens_per_day, encoding_name to application.yml
    query_manager = LLMQueryManager(use_llm=use_llm, tier=tier, system_prompt=system_prompt, cached_prompt=cached_prompt,
                                    max_calls=1000,
                                    period=60,
                                    max_tokens_per_min=80000,
                                    max_tokens_per_day=2500000,
                                    encoding_name="cl100k_base")
    
    return query_manager


def extract_and_process_next_steps(response: str, pf: ProjectFiles) -> Tuple[str, str, bool]:
    """
    Extract 'Next Steps' from LLM response, process requests, and prepare new information.
    
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

        elif "[I need external API response for:" in line:
            # parse the API name, endpoint, and parameters
            api_name = re.search(r'<api>(.*?)</api>', line).group(1)
            endpoint = re.search(r'<endpoint>(.*?)</endpoint>', line).group(1)
            params = re.search(r'<params>(.*?)</params>', line).group(1)
            # make the API call
            api_response = make_api_call(api_name, endpoint, params)
            new_information += f"\nYou requested external API response for '{api_name}'\nHere is the response: {api_response}\n"
        elif "[I need database query results for:" in line:
            # parse the database name and query
            database_name = re.search(r'<db>(.*?)</db>', line).group(1)
            query = re.search(r'<query>(.*?)</query>', line).group(1)
            # make the database query
            db_response = make_db_query(database_name, query)
            new_information += f"\nYou requested database query results for '{database_name}'\nHere is the response: {db_response}\n"
        else:
            pass # ignore the line
        i += 1


    # Remove the **Next Steps** section and everything following it
    updated_response = response[:next_steps_index].strip()

    return new_information, updated_response, stop_function_prompt


def query_llm(query_manager, question, user_prompt_template, instruction_prompt, last_response, pf, iteration_number: str="", new_information: str="", key_findings: List[str]=[], stop_function_prompt: bool=False, reviewer: ConversationReviewer=None) -> Tuple[str, str, bool, List[str]]:
    """
    return new_information, response, stop_function_prompt, updated_key_findings
    """
    user_prompt = user_prompt_template.format(
        iteration_number=iteration_number,
        question=question,
        previous_llm_response=last_response,
        do_not=do_not_search_prompt.format(not_found_terms=not_found_terms()),
        new_information=str(new_information) if new_information else "",
        key_findings="\n".join(key_findings) if key_findings else "",
        instructions=instruction_prompt,
        function_prompt=function_prompt if not stop_function_prompt else "",
    )
    response = query_manager.query(user_prompt)
    # update the tracing with the iteration number
    langfuse_context.update_current_observation(tags=[iteration_number])

    #TODO: Cross-check response against key findings
    inconsistencies = cross_check_response(response, key_findings)
    if inconsistencies:
        correction_prompt = f"""
        Your response has the following inconsistencies with previously identified key points:
        {inconsistencies}
        Please provide a corrected response that addresses these inconsistencies.
        """
        response = query_manager.query(correction_prompt)
    
    if reviewer is not None:
        # Add the conversation to the reviewer's history
        if iteration_number != "0":
            reviewer.add_conversation(new_information, response)
        else:
            reviewer.add_conversation(question, response)
        
        # Only review every 2 rounds, and not the first round
        if int(iteration_number) % 2 == 1:
            should_continue, final_answer_prompt = reviewer.should_continue_conversation()
            if not should_continue:
                logger.info("The conversation reviewer does not want to continue the conversation")
                if final_answer_prompt is not None:
                    logger.info(f"The conversation reviewer final answer prompt: {final_answer_prompt}")
                    # TODO: add the final_answer_prompt to the response ...

                # make sure to remove anything that after the **Next Steps** section
                next_steps_index = response.find("**Next Steps**")
                if next_steps_index != -1:
                    response = response[:next_steps_index]
                return None, response, True, key_findings
    # Extract and update key findings
    new_key_findings = extract_key_findings(response)
    updated_key_findings = update_key_findings(key_findings, new_key_findings)
    
    try:
        new_information, response, stop_function_prompt = extract_and_process_next_steps(response, pf)
    except Exception as e:
        logger.error(f"An error occurred in extract_and_process_next_steps: {str(e)}", exc_info=True)
        return None, response, True, key_findings
    
    return new_information, response, stop_function_prompt, updated_key_findings

def extract_key_findings(response):
    key_findings = []
    key_findings_section = re.search(r'KEY_FINDINGS:(.*?)(?=\n\n|\Z)', response, re.DOTALL)
    if key_findings_section:
        findings = key_findings_section.group(1).strip().split('\n')
        for finding in findings:
            finding = finding.strip()
            if finding.startswith('- ['):
                key_findings.append(finding)
    return key_findings

def update_key_findings(old_findings, new_findings):
    # Combine old and new findings
    all_findings = old_findings + new_findings
    # Remove duplicates while preserving order
    unique_findings = []
    seen = set()
    for finding in all_findings:
        if finding not in seen:
            unique_findings.append(finding)
            seen.add(finding)
    # Limit to top 15 findings (you can adjust this number)
    return unique_findings[:15]

def cross_check_response(response, key_findings):
    # Implement logic to check if all key findings are reflected in the response
    pass
