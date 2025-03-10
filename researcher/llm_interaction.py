import re
import os
from typing import List, Tuple, Optional
from gist.projectfiles import ProjectFiles
from llm_client import LLMQueryManager, langfuse_context
from .conversation_reviewer import ConversationReviewer
import logging
import string
from .functions import (
    do_not_search_prompt,
    efficient_file_search, 
    read_files, 
    read_packages, 
    process_file_request, 
    get_static_notes
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Remove the initiate_llm_query_manager function from this file
# and import it from llm_utils instead
from llm_utils import count_tokens

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

def query_llm(query_manager, question, user_prompt_template, instruction_prompt, function_prompt, last_response, pf, iteration_number, new_information, key_findings, reviewer=None):
    """
    Query the LLM with the given parameters.
    """
    try:
        # Check if we should include the function prompt
        # Only include it on certain iterations (e.g., 1st, 4th, 7th, etc.)
        include_function_prompt = (
            bool(iteration_number) and 
            iteration_number != "final" and  # Skip this check for the "final" iteration
            int(iteration_number) % 3 == 1
        )
        
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

        # Extract and update key findings - only call extract_key_findings once
        new_key_findings = extract_key_findings(response)
        logger.info(f"new_key_findings: {new_key_findings}")
        updated_key_findings = update_key_findings(key_findings, new_key_findings)
        logger.info(f"updated_key_findings: {updated_key_findings}")

        try:
            new_information = extract_and_process_next_steps(response, pf)
            # Pass the updated_key_findings to shoud_continue_conversation
            should_continue, final_answer_prompt = shoud_continue_conversation(
                question, response, new_information, reviewer, 
                include_function_prompt,
                key_findings=updated_key_findings
            )

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
            raise
    except Exception as e:
        logger.error(f"An error occurred in query_llm: {str(e)}", exc_info=True)
        raise

def shoud_continue_conversation(question, response, new_information, conversation_reviewer: ConversationReviewer, check_history: bool=True, key_findings=None):
    # Check if there are file or package requests in the response
    has_file_requests = any(x in response for x in ["[I need to search", "[I need content of files:", "[I need info about packages:"])
    
    if not new_information and has_file_requests:
        logger.info("File or package requests detected but no information was retrieved. This might indicate a processing issue.")
        # Return True to continue the conversation despite no new information
        return True, None
    elif not new_information:
        logger.info("The conversation should stop now that there is no new information found.")
        return False, None
        
    if not conversation_reviewer:
        return True, None
    
    # Add state-related metadata to conversation context
    if hasattr(conversation_reviewer, 'update_conversation_context'):
        # Use the provided key_findings instead of extracting them again
        has_code = "```" in response
        
        # Update context based on response content
        conversation_reviewer.update_conversation_context(
            question=question,
            has_code_examples=has_code,
            has_file_requests=has_file_requests,
            confidence=0.7 if key_findings else 0.5,  # Simple heuristic for confidence
            found_key_findings=(key_findings and len(key_findings) > 0)
        )
        
        # Check for indicators that might trigger state transitions
        ambiguities_detected = "unclear" in response.lower() or "ambiguous" in response.lower()
        if ambiguities_detected:
            conversation_reviewer.update_conversation_context(ambiguities_detected=True)
    
    # review the conversation so far
    if conversation_reviewer.is_history_empty():
        conversation_reviewer.add_conversation(question, response)
    else:
        conversation_reviewer.add_conversation(new_information, response)

    if check_history:
        should_continue, final_answer_prompt = conversation_reviewer.should_continue_conversation()
    else:
        should_continue, final_answer_prompt = True, None
        
    # Log the current conversation state if available
    if hasattr(conversation_reviewer, 'get_current_state'):
        current_state = conversation_reviewer.get_current_state()
        logger.info(f"Current conversation state: {current_state.value}")
        
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

def extract_and_process_next_steps(response: str, pf: ProjectFiles) -> str:
    """
    Extract and process next steps from the LLM response.
    Returns new information to be added to the next prompt.
    """
    if not pf:
        return ""
        
    lines = response.split('\n')
    i = 0
    new_information = ""
    has_requests = False
    has_new_information = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Search for files
        if "[I need to search" in line:
            has_requests = True
            request_text = line
            
            # Collect the full request text which might span multiple lines
            while i < len(lines) and ']' not in request_text:
                i += 1
                if i < len(lines):
                    request_text += ' ' + lines[i].strip()
            
            # Process search request
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
        
        # Request for file content
        elif "[I need content of files:" in line:
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
        
        # Request for package information
        elif "[I need info about packages:" in line:
            has_requests = True
            request_text = line
            
            # Collect the full request text which might span multiple lines
            while i < len(lines) and ']' not in request_text:
                i += 1
                if i < len(lines):
                    request_text += ' ' + lines[i].strip()
            
            # Extract package names using regex
            package_pattern = r'<package>(.*?)</package>'
            packages = re.findall(package_pattern, request_text)
            
            if packages:
                for package in packages:
                    logger.info(f"LLM needs package info: {package}")
                    package_info = read_packages(pf, [package])
                    if package_info:
                        new_information += f"\nPackage information for '{package}':\n{package_info}\n"
                        has_new_information = True
                    else:
                        new_information += f"\nNo information found for package '{package}'\n"
                        has_new_information = True  # Consider "no results" as new information
            else:
                # If we couldn't extract package names
                logger.warning(f"Could not extract package names from request: {request_text}")
                new_information += "\nI couldn't understand your package information request. Please use the format: [I need info about packages: <package>package.name</package>]\n"
                has_new_information = True
        
        i += 1

    if not has_requests:
        return ""

    return new_information

def remove_next_steps(response) -> str:
    return response.replace("**Next Steps**", "AI requested more info").strip()
