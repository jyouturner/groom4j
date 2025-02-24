import re
import os
from typing import List, Tuple, Optional
from projectfiles import ProjectFiles
from functions import efficient_file_search, read_files, read_packages, process_file_request, get_static_notes
from functions import make_api_call, make_db_query
from functions import do_not_search_prompt
from llm_client import LLMQueryManager, langfuse_context
from conversation_reviewer import ConversationReviewer
import logging
import string
from prompts import system_prompt_answer_question
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# the global search results dict with key being the search keyword, the value being a list of file names, or [] if no matching files
# this is important to avoid repeated search for the same keyword
global_search_results = {}

# Add at the top with other globals
global_failed_file_requests = set()

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
    # Get max_tokens from environment if available
    max_tokens_tier1 = int(os.environ.get("LLM_MAX_TOKENS_TIER1", "4096"))
    max_tokens_tier2 = int(os.environ.get("LLM_MAX_TOKENS_TIER2", "2048"))
    max_tokens = max_tokens_tier1 if tier == "tier1" else max_tokens_tier2
    
    # prompts can be reused and cached in the LLM if it is supported
    if pf is not None:
        package_notes = get_static_notes(pf)
        project_tree = pf.to_tree()
        file_notes = pf.get_file_notes()
        # check the token size limit
        tokenSize = count_tokens(package_notes)
        if tokenSize > 200000:
            #raise ValueError("The system_prompt exceeds the maximum token limit")
            # reduce the size of package notes
            package_notes = package_notes[:120000]
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
                                    max_tokens=max_tokens,
                                    max_calls=1000,
                                    period=60,
                                    max_tokens_per_min=80000,
                                    max_tokens_per_day=2500000,
                                    encoding_name="cl100k_base")
    
    return query_manager


def extract_and_process_next_steps(response: str, pf: ProjectFiles) -> str:
    """Extract and process next steps from the response."""
    new_information = ""
    
    # Process the entire response for any type of request
    lines = response.split("\n")
    i = 0
    has_requests = False
    has_new_information = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Handle file requests
        if "[I need content of files:" in line or "[I need access files:" in line:
            has_requests = True
            # Extract everything between : and ] with improved multiline support
            request_text = line
            j = i
            while j < len(lines) and ']' not in request_text:
                j += 1
                if j < len(lines):
                    request_text += ' ' + lines[j].strip()
            
            # Extract file names using process_file_request
            file_names = process_file_request([request_text])
            
            if file_names:
                logger.info(f"need files {file_names}")
                
                # Filter out previously failed requests
                new_files = [f for f in file_names if f not in global_failed_file_requests]
                if not new_files:
                    new_information += "\nThe requested files were previously not found or are not accessible. Please proceed with available information.\n"
                    i = j + 1
                    continue

                file_contents, files_found, files_not_found = read_files(pf, new_files)
                
                # Track failed requests
                global_failed_file_requests.update(files_not_found)
                
                if file_contents:
                    new_information += file_contents
                    has_new_information = True
                if files_not_found:
                    not_found_msg = f"\nThe following files could not be found or accessed: {', '.join(files_not_found)}\n"
                    new_information += not_found_msg
                    logger.info(not_found_msg)
                
                logger.info(f"files_found: {files_found}")
                logger.info(f"files_not_found: {files_not_found}")
                
                i = j + 1
                continue
        
        # Handle search requests with more flexible pattern matching
        elif "[I need to search" in line:
            has_requests = True
            request_text = line
            while i < len(lines) and ']' not in request_text:
                i += 1
                if i < len(lines):
                    request_text += ' ' + lines[i].strip()
            
            # Try multiple patterns to extract keywords
            keywords = []
            
            # Pattern 1: <keyword>text</keyword>
            tag_pattern = r'<keyword>(.*?)</keyword>'
            tag_keywords = re.findall(tag_pattern, request_text)
            if tag_keywords:
                keywords.extend(tag_keywords)
            
            # Pattern 2: keywords: keyword1, keyword2
            if not keywords and "keywords:" in request_text:
                keyword_text = re.search(r'keywords:\s*([^\]]+)', request_text)
                if keyword_text:
                    raw_keywords = keyword_text.group(1).split(',')
                    keywords.extend([k.strip() for k in raw_keywords if k.strip()])
            
            # Pattern 3: keywords: single phrase without commas
            if not keywords and "keywords:" in request_text:
                keyword_text = re.search(r'keywords:\s*([^\]]+)', request_text)
                if keyword_text:
                    keywords = [keyword_text.group(1).strip()]
            
            # Pattern 4: for keywords: phrase
            if not keywords and "for keywords:" in request_text:
                keyword_text = re.search(r'for keywords:\s*([^\]]+)', request_text)
                if keyword_text:
                    keywords = [keyword_text.group(1).strip()]
            
            if keywords:
                for keyword in keywords:
                    logger.info(f"LLM needs to search: {keyword}")
                    
                    # Skip already searched keywords
                    if keyword in global_search_results:
                        new_information += f"\nYou already searched for '{keyword}'. Using previous results.\n"
                        if global_search_results[keyword]:
                            files_str = ', '.join(f"<file>{file}</file>" for file in global_search_results[keyword])
                            new_information += f"Here are results: {files_str}\n"
                        else:
                            new_information += f"No matching files were found.\n"
                        has_new_information = True
                        continue
                    
                    matching_files = efficient_file_search(pf.root_path, keyword)
                    global_search_results[keyword] = matching_files
                    if matching_files:
                        files_str = ', '.join(f"<file>{file}</file>" for file in matching_files)
                        new_information += f"\nYou requested to search for '{keyword}'\nHere are results: {files_str}\n"
                        has_new_information = True
                    else:
                        new_information += f"\nNo matching files found with '{keyword}'\n"
                        has_new_information = True  # Consider "no results" as new information
            else:
                # If we couldn't extract keywords with any pattern, log the issue
                logger.warning(f"Could not extract keywords from search request: {request_text}")
                new_information += "\nI couldn't understand your search request. Please use the format: [I need to search for keywords: <keyword>keyword</keyword>]\n"
                has_new_information = True
        
        i += 1

    if not has_requests:
        return ""

    return new_information

def remove_next_steps(response) -> str:
    return response.replace("**Next Steps**", "AI requested more info").strip()

def query_llm(query_manager, question, user_prompt_template, instruction_prompt, function_prompt, last_response, pf, iteration_number: str="", new_information: str="", key_findings: List[str]=[], reviewer: ConversationReviewer=None) -> Tuple[str, str, bool, List[str], str]:
    """
    query the LLM with the given question, user_prompt_template, instruction_prompt, last_response, pf, iteration_number, new_information, key_findings, reviewer
    process the response and update the key findings
    review the conversation and decide whether to continue the conversation
    return new_information, response, should_conclude, key_findings, final_answer_prompt
    """
    # Prepare a dictionary of format parameters
    format_params = {
        "iteration_number": iteration_number,
        "question": question,
        "previous_llm_response": last_response,
        "do_not": do_not_search_prompt.format(not_found_terms=not_found_terms()),
        "new_information": str(new_information) if new_information else "",
        "key_findings": "\n".join(key_findings) if key_findings else "",
        "instructions": instruction_prompt,
        "function_prompt": function_prompt
    }

    # Filter out keys that are not in the template
    template_keys = [key[1] for key in string.Formatter().parse(user_prompt_template) if key[1] is not None]
    filtered_params = {k: v for k, v in format_params.items() if k in template_keys}

    # Format the user prompt
    user_prompt = user_prompt_template.format(**filtered_params)

    # query LLM
    response = query_manager.query(user_prompt)

    # debug to print the end 500 characters of the response
    logger.info(f"LLM response: {response[-500:]}")

    # update the tracing with the iteration number
    langfuse_context.update_current_observation(tags=[iteration_number])

    #TODO: Cross-check response against key findings
    inconsistencies = cross_check_response(response, key_findings)
    if inconsistencies:
        pass

    # Extract and update key findings
    new_key_findings = extract_key_findings(response)
    logger.info(f"new_key_findings: {new_key_findings}")
    updated_key_findings = update_key_findings(key_findings, new_key_findings)
    logger.info(f"updated_key_findings: {updated_key_findings}")

    
    try:
        new_information = extract_and_process_next_steps(response, pf)
        # record the conversation and decide whether to continue the conversation
        should_continue, final_answer_prompt = shoud_continue_conversation(question, response, new_information, reviewer, bool(iteration_number) and int(iteration_number) % 3 == 1)

        # if reviwer suggest to conclude the conversation, then we use the final_answer_prompt as the prompt to LLM
        # to have the last conversation
        if not should_continue and final_answer_prompt:
            updated_response = final_answer_prompt
        else:
            # make sure to remove anything that after the **Next Steps** section since it is already processed
            updated_response = remove_next_steps(response)

        return new_information, updated_response, not should_continue, updated_key_findings, final_answer_prompt
    except Exception as e:
        logger.error(f"An error occurred in query_llm: {str(e)}", exc_info=True)
        return None, response, True, updated_key_findings, None

def shoud_continue_conversation(question, response, new_information, conversation_reviewer: ConversationReviewer, check_history: bool=True):
    if not new_information:
        logger.info("the conversation should stop now that there is no new information found.")
        return False, None
    if not conversation_reviewer:
        return True, None
    # review the conversation so far
    if conversation_reviewer.is_history_empty():
        conversation_reviewer.add_conversation(question, response)
    else:
        conversation_reviewer.add_conversation(new_information, response)

    if check_history:
        should_continue, final_answer_prompt = conversation_reviewer.should_continue_conversation()
    else:
        should_continue, final_answer_prompt = True, None
    logger.info(f"New information is requested, and the conversation reviewer decided the conversation should_continue={should_continue}")
    return should_continue, final_answer_prompt

def extract_key_findings(response):
    key_findings = []
    key_findings_section = re.search(r'\*?\*?KEY_FINDINGS\*?\*?:(.*?)(?=\n\n|\Z)', response, re.DOTALL | re.IGNORECASE)
    if key_findings_section:
        findings = key_findings_section.group(1).strip().split('\n')
        for finding in findings:
            finding = finding.strip()
            if re.match(r'[-\*]?\s*\*?\[(BUSINESS_RULE|IMPLEMENTATION_DETAIL|DATA_FLOW|ARCHITECTURE|SPECIAL_CASE)\]\*?', finding):
                # Remove leading dash or asterisk and surrounding asterisks, if present
                finding = re.sub(r'^[-\*]?\s*\*?|\*?$', '', finding).strip()
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


import tiktoken

def count_tokens(text):
    encoding = tiktoken.get_encoding("gpt2")
    return len(encoding.encode(text))
