from typing import Tuple
import os
import sys
import re
import argparse
import yaml
import time
from embedding.embedding_config import EmbeddingConfig
from gist.projectfiles import ProjectFiles
from typing import Union, Optional, List, Dict, Any
from functions import get_file, get_package, get_static_notes
from functions import efficient_file_search, read_files, read_packages, read_all_packages, read_from_human
from functions import process_file_request
from functions import save_response_to_markdown
from functions import function_prompt

import logging

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()

from rewrite_question import decompose_question, system_prompt_rewrite_question

from llm_client import LLMQueryManager, langfuse_context, observe
from conversation_reviewer import ConversationReviewer
from llm_utils import initiate_llm_query_manager
from llm_interaction import query_llm
from conversation_state_machine import generate_state_transition_diagram, save_conversation_with_states
from memory.memory_manager import MemoryManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

system_prompt = """
You are an AI assistant designed to help Java developers understand and analyze existing Java projects. 
"""


instructions = """
Begin by exploring the codebase broadly:
1. First, search for direct mentions of the key concepts (using multiple search terms and variations)
2. Identify key files that might be relevant to the functionality
3. Examine relationships between these files (imports, method calls, shared constants)
4. Create a mental map of how the feature is implemented across multiple components

Show your reasoning by:
- Explaining why you're looking at specific files
- Connecting insights across different files
- Building a coherent understanding of the overall system

Then, dive into specific details:
1. Start with a high-level overview of relevant components.
2. Dive deeper into specific areas as needed, leveraging the project structure and codebase.
3. Provide clear, concise explanations.
4. If you're unsure about something, state it clearly.
5. The goal is to be as thorough as possible to answer the questions effectively.

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

As you gather information, periodically synthesize your findings:
1. After examining each key file, summarize what you've learned
2. Connect new information with your previous findings
3. Revise your understanding if new evidence contradicts earlier conclusions
4. Identify remaining gaps in your understanding
5. Prioritize next steps based on these gaps

Your final answer should show a clear progression from individual code components to a comprehensive understanding of the system behavior.
"""



reused_prompt_template = """

Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}


"""

reused_prompt_template_answer_question = """
Below is the Java project structure for your reference:
{project_tree}

and summaries of the packages in the project:
{package_notes}

Please analyze the code and provide detailed answers.
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

As you gather information, periodically synthesize your findings:
1. After examining each key file, summarize what you've learned
2. Connect new information with your previous findings
3. Revise your understanding if new evidence contradicts earlier conclusions
4. Identify remaining gaps in your understanding
5. Prioritize next steps based on these gaps

Your final answer should show a clear progression from individual code components to a comprehensive understanding of the system behavior.

As you analyze the code:
- Show your search strategy and results
- Explain why you're examining specific files
- Share insights as you discover them
- Connect new findings to your developing understanding
- Identify and resolve contradictions in your understanding

Make your thinking visible so the user can follow your investigation process.
"""

final_user_prompt_template = """

===QUESTION===
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



@observe(name="answer_question", capture_input=True, capture_output=True)
def answer_question(pf: Optional[ProjectFiles], question, last_response="", thoroughness=6, max_rounds=8):
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
    
    # Initialize memory configuration
    embedding_config, vector_store_config = initialize_memory_config()
    print(f"Embedding config: {embedding_config} \n\nVector store config: {vector_store_config}")
    
    # Initialize the conversation reviewer with memory support
    reviewer = ConversationReviewer(
        query_manager=query_manager_tier2, 
        target_thoroughness=thoroughness, 
        max_rounds=max_rounds,
        use_memory=True,
        embedding_config=embedding_config,
        vector_store_config=vector_store_config
    )
    
    # Initialize memory if project root is available
    if pf and hasattr(pf, 'root_path'):
        reviewer.initialize_memory(pf.root_path)
    
    # Get memory context for the question if available
    memory_context = ""
    if hasattr(reviewer, 'get_relevant_memories'):
        memory_context = reviewer.get_relevant_memories(question)
        if memory_context:
            # Add memory context to the initial prompt
            new_information = f"Relevant information from previous conversations:\n{memory_context}\n\n"
    
    # Initialize conversation context with question metadata
    if hasattr(reviewer, 'update_conversation_context'):
        reviewer.update_conversation_context(
            question=question,
            question_received=True,
            user_expertise="medium",  # Default expertise level
            max_rounds=max_rounds,
            memories_context=memory_context,
            relevant_memories_found=(memory_context != "")
        )
        reviewer.current_question = question  # Set current question for memory storage
    
    final_answer_prompt = None
    should_conclude = False
    while i < max_rounds:
        logger.info(f"--------- Round {i} ---------")
        
        # Update reviewer context with current round information
        if hasattr(reviewer, 'update_conversation_context'):
            reviewer.update_conversation_context(
                round=i,
                remaining_rounds=max_rounds - i
            )
            
        # Log current conversation state
        if hasattr(reviewer, 'get_current_state'):
            current_state = reviewer.get_current_state()
            logger.info(f"Current conversation state: {current_state.value}")
            
            # Get state-specific guidance for instruction prompt
            if hasattr(reviewer, 'get_state_prompt_guidance'):
                state_guidance = reviewer.get_state_prompt_guidance()
                if state_guidance:
                    logger.info(f"Adding state guidance: {state_guidance}")
                    # Could modify instruction_prompt with state_guidance here if desired
        
        try:
            new_information, last_response, should_conclude, key_findings, final_answer_prompt = query_llm_with_retry(
                query_manager=query_manager,
                question=question,
                user_prompt_template=user_prompt_template,
                instruction_prompt=instructions,
                function_prompt=function_prompt,
                last_response=last_response,
                pf=pf,
                iteration_number=str(i),
                new_information=new_information,
                key_findings=key_findings,
                reviewer=reviewer
            )
            
            logger.info(f"Last response: {last_response[:100]}...")
            
            # Update context with key findings
            if hasattr(reviewer, 'update_conversation_context') and key_findings:
                reviewer.update_conversation_context(
                    key_findings=key_findings,
                    found_key_findings=True
                )
            
            if should_conclude:
                logger.info("The conversation is about to end")
                
                # Force state to concluding before final answer
                if hasattr(reviewer, 'state_manager') and hasattr(reviewer.state_manager, 'state_machine'):
                    from conversation_state_machine import ConversationState
                    old_state = reviewer.state_manager.state_machine.current_state
                    reviewer.state_manager.state_machine.current_state = ConversationState.CONCLUDING
                    reviewer.state_manager.log_state_transition(
                        old_state, 
                        ConversationState.CONCLUDING, 
                        "Concluding conversation"
                    )
                
                # Check if we're in a test environment before making the extra call
                import inspect
                is_test = any('unittest' in frame.filename for frame in inspect.stack())
                
                if final_answer_prompt and not is_test:
                    logger.info("Using final answer prompt")
                    new_information, last_response, _, key_findings, _ = query_llm_with_retry(
                        query_manager=query_manager,
                        question=question,
                        user_prompt_template=final_user_prompt_template,
                        instruction_prompt=final_answer_prompt,
                        function_prompt="",
                        last_response=last_response,
                        pf=pf,
                        iteration_number="final",
                        new_information=new_information,
                        key_findings=key_findings,
                        reviewer=None
                    )
                    
                # Save conversation state for future reference
                if hasattr(reviewer, 'save_state'):
                    try:
                        import os
                        state_dir = os.path.join(pf.root_path, ".gist", "conversation_states")
                        os.makedirs(state_dir, exist_ok=True)
                        state_file = os.path.join(state_dir, f"state_{int(time.time())}.json")
                        reviewer.save_state(state_file)
                        logger.info(f"Saved conversation state to {state_file}")
                    except Exception as e:
                        logger.error(f"Failed to save conversation state: {str(e)}")
                        
                # Save final conversation to memory
                if reviewer and not is_test:
                    save_conversation_to_memory(
                        reviewer=reviewer,
                        question=question,
                        response=last_response,
                        key_findings=key_findings
                    )
                
                break
            
        except Exception as e:
            logger.error(f"An error occurred in round {i}: {str(e)}", exc_info=True)
            break
            
        i += 1
        
        # Check if we're about to hit the max rounds limit
        if i >= max_rounds and not should_conclude:
            logger.info(f"Reached maximum rounds ({max_rounds}), generating final summary...")
            
            # Force the state to concluding
            if hasattr(reviewer, 'state_manager') and hasattr(reviewer.state_manager, 'state_machine'):
                from conversation_state_machine import ConversationState
                old_state = reviewer.state_manager.state_machine.current_state
                reviewer.state_manager.state_machine.current_state = ConversationState.CONCLUDING
                reviewer.state_manager.log_state_transition(
                    old_state, 
                    ConversationState.CONCLUDING, 
                    f"Max rounds ({max_rounds}) reached, forcing conclusion"
                )
            
            # Generate a final synthesis prompt
            final_synthesis_prompt = f"""
            You have now spent {max_rounds} rounds analyzing this question. Based on all the information 
            you've gathered so far, please provide a final comprehensive answer that:
            
            1. Synthesizes all key findings
            2. Explains how the relevant code components work together
            3. Addresses the original question directly and completely
            4. Acknowledges any remaining uncertainties
            
            This is your final opportunity to provide the most helpful answer possible.
            """
            
            # Execute one final round with the synthesis prompt
            _, last_response, _, key_findings, _ = query_llm_with_retry(
                query_manager=query_manager,
                question=question,
                user_prompt_template=final_user_prompt_template,
                instruction_prompt=final_synthesis_prompt,
                function_prompt="",  # No need for function prompt in the final synthesis
                last_response=last_response,
                pf=pf,
                iteration_number="final",
                new_information=new_information,
                key_findings=key_findings,
                reviewer=None  # Skip review for final summary
            )
            
            # Save conversation to memory
            import inspect
            is_test = any('unittest' in frame.filename for frame in inspect.stack())
            if reviewer and not is_test:
                save_conversation_to_memory(
                    reviewer=reviewer,
                    question=question,
                    response=last_response,
                    key_findings=key_findings
                )
            
            break
    
    logger.info(f"Total rounds: {i}")
    # Use get_total_tokens instead of get_token_usage
    try:
        total_tokens = query_manager.get_total_tokens()
        logger.info(f"Total tokens: {total_tokens}")
    except (AttributeError, TypeError) as e:
        logger.info(f"Token usage information not available: {str(e)}")
    
    return last_response, reviewer



def break_down_and_answer(question: str, pf: Optional[ProjectFiles], root_path: str, max_rounds=10, thoroughness=6) -> None:
    """
    Rewrite the question, answer the decomposed questions, and save the responses to markdown files.

    Args:
        question (str): The original question to be processed.
        pf: The ProjectFiles object.
        root_path (str): The root directory where the files will be saved.
        max_rounds: max rounds of conversation with LLM before exit.
        thoroughness: thoroughness level for the conversation reviewer.
    """
    query_manager = initiate_llm_query_manager(pf=None, system_prompt=system_prompt_rewrite_question, reused_prompt_template=None)
    decompose_questions, refined_question = decompose_question(query_manager, question)
    
    # Record the answers to the decomposed questions
    research_notes = ""
    decomposed_links = []
    final_reviewer = None
    for q in decompose_questions:
        logger.info(f"Question: {q}")
        response, reviewer = answer_question(pf, q, last_response="", max_rounds=max_rounds, thoroughness=thoroughness)
        final_reviewer = reviewer  # Keep the last reviewer
        logger.info(response)
        research_notes += f"\n\n===Question: {q}===\n\n{response}"
        # Write to a markdown file, in root_path/.gist/tell_me_about/
        result_file = save_response_to_markdown(q, response, path=root_path+"/.gist/tell_me_about/")
        decomposed_links.append(f"- [{q}]({os.path.basename(result_file)})")
        logger.info(f"Response saved to {result_file}")

    # Now let's answer the refined question with answers to the decomposed questions
    response, reviewer = answer_question(pf, refined_question, last_response=research_notes, max_rounds=max_rounds, thoroughness=thoroughness)
    final_reviewer = reviewer  # Use the final reviewer
    
    # Prepare the final content with links to decomposed questions
    final_content = "# Refined Answer\n\n" + response + "\n\n## Decomposed Questions\n\n" + "\n".join(decomposed_links)
    
    # Save to markdown file
    result_file = save_response_to_markdown(question, final_content, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")
    return response, final_reviewer

def read_last_question_from_markdown(file_path: str) -> tuple[Optional[str], str]:
    """
    Read the last user question and full conversation history from a markdown conversation file.
    Returns (last_question, conversation_history) where last_question can be None if not found.
    Conversation history includes all previous exchanges between User and Agent, reading answer content from linked files.
    """
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        last_question = None
        in_user_section = False
        current_question = []
        has_answer = False
        conversation_parts = []
        
        for line in lines:
            if line.startswith('## User'):
                if in_user_section and not has_answer:
                    last_question = ''.join(current_question).strip()
                in_user_section = True
                current_question = []
                has_answer = False
                # conversation_parts.append(line) the question is already in the answer file
            elif line.startswith('## Agent'):
                in_user_section = False
                has_answer = True
   
            elif in_user_section:
                if line.strip() and line.strip() not in ['[user question]', '[whatever the user wants to ask]']:
                    current_question.append(line)
       
            elif '[Answer](' in line:
                # Extract and read the linked answer file
                answer_path = line.split('(')[1].split(')')[0]
                full_path = os.path.join(os.path.dirname(file_path), answer_path)
                try:
                    with open(full_path, 'r') as af:
                        answer_content = af.read()
                    conversation_parts.append(answer_content + '\n')
                except Exception as e:
                    logger.error(f"Error reading answer file {full_path}: {str(e)}")
                    conversation_parts.append(line)
            else:
                conversation_parts.append(line)
        
        # Check the last section
        if in_user_section and not has_answer and current_question:
            last_question = ''.join(current_question).strip()
        
        conversation_text = ''.join(conversation_parts).strip()
        
        if last_question:
            logger.info(f"Found question: {last_question}")
        else:
            logger.info("No unanswered questions found in markdown file")
            
        return last_question, conversation_text
            
    except Exception as e:
        logger.error(f"Error reading markdown file: {str(e)}")
        return None, ""

def update_markdown_with_answer(file_path: str, answer_file: str):
    """
    Update the markdown file by appending the new answer as an Agent section with a link.
    """
    try:
        relative_path = os.path.relpath(answer_file, os.path.dirname(file_path))
        
        with open(file_path, 'a') as f:
            f.write('\n## Agent\n\n')
            f.write(f'[Answer]({relative_path})\n')
            
        logger.info(f"Updated conversation file with answer link: {relative_path}")
            
    except Exception as e:
        logger.error(f"Error updating markdown file: {str(e)}")

def process_conversation_file(conversation_file: str, project_root: str, thoroughness: int = 6, max_rounds: int = 8):
    """
    Process a conversation markdown file, reading the last question and generating an answer.
    """
    # Read the last unanswered question
    question, conversation_history = read_last_question_from_markdown(conversation_file)

    if not question:
        logger.error("No valid question found in conversation file")
        return
    
    logger.info(f"Processing question: {question}")
    
    # Initialize ProjectFiles
    root_path = os.path.abspath(project_root)
    if not os.path.exists(root_path):
        logger.error(f"Error: {root_path} does not exist")
        return
        
    pf = ProjectFiles(repo_root_path=root_path)
    pf.from_gist_files()
    
    
    # Generate answer
    reviewer = None  # Initialize reviewer variable
    try:
        if "--breakdown" in sys.argv:
            res, reviewer = break_down_and_answer(question, pf, root_path, max_rounds=max_rounds, thoroughness=thoroughness)
        else:
            res, reviewer = answer_question(pf, question, thoroughness=thoroughness, max_rounds=max_rounds)
            
        # Save response and update conversation file
        result_file = save_response_to_markdown(question, res, path=root_path+"/.gist/tell_me_about/")
        update_markdown_with_answer(conversation_file, result_file)
        logger.info(f"Response saved to {result_file} and conversation updated")
        
        # Save to memory if reviewer supports it
        if reviewer and hasattr(reviewer, '_save_conversation_to_memory'):
            try:
                reviewer._save_conversation_to_memory()
                logger.info("Conversation saved to memory")
            except Exception as e:
                logger.error(f"Error saving conversation to memory: {str(e)}")
        
        # Generate state transition diagram if state tracking was used
        if reviewer and hasattr(reviewer, 'state_manager') and hasattr(reviewer.state_manager, 'conversation_history'):
            try:
                from conversation_state_machine import generate_state_transition_diagram, save_conversation_with_states
                import time
                
                # Create diagrams directory if needed
                diagrams_dir = os.path.join(root_path, ".gist", "state_diagrams")
                os.makedirs(diagrams_dir, exist_ok=True)
                
                # Generate and save diagram
                diagram = generate_state_transition_diagram(reviewer.state_manager.conversation_history)
                diagram_file = os.path.join(diagrams_dir, f"diagram_{int(time.time())}.md")
                with open(diagram_file, 'w') as f:
                    f.write("# Conversation State Diagram\n\n")
                    f.write("```mermaid\n")
                    f.write(diagram)
                    f.write("\n```\n")
                
                # Save full conversation with states
                conversation_state_file = os.path.join(diagrams_dir, f"conversation_{int(time.time())}.md")
                save_conversation_with_states(reviewer.state_manager.conversation_history, conversation_state_file)
                
                logger.info(f"Generated state transition diagram at {diagram_file}")
                logger.info(f"Saved conversation with state tracking at {conversation_state_file}")
            except Exception as e:
                logger.error(f"Failed to generate state transition diagram: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)

def query_llm_with_retry(query_manager, question, user_prompt_template, instruction_prompt, function_prompt, last_response, pf, iteration_number, new_information, key_findings, reviewer, max_retries=2):
    """
    Query the LLM with retry mechanism for file requests that fail.
    """
    retry_count = 0
    while retry_count <= max_retries:
        new_info, response, should_conclude, updated_key_findings, final_answer_prompt = query_llm(
            query_manager=query_manager,
            question=question,
            user_prompt_template=user_prompt_template,
            instruction_prompt=instruction_prompt,
            function_prompt=function_prompt,
            last_response=last_response,
            pf=pf,
            iteration_number=iteration_number,
            new_information=new_information,
            key_findings=key_findings,
            reviewer=reviewer
        )
        
        # If we got new information or should conclude, return the results
        if new_info or should_conclude or "NONE" in response:
            return new_info, response, should_conclude, updated_key_findings, final_answer_prompt
        
        # If we didn't get new information but the response contains file requests,
        # modify the prompt to suggest alternative files
        if "[I need content of files:" in response or "[I need access files:" in response:
            logger.info(f"File request failed, retrying with modified prompt (attempt {retry_count+1}/{max_retries})")
            last_response = response + "\n\nNote: The requested files could not be found. Please try with different file names or proceed with the information you have."
            retry_count += 1
        else:
            # If there are no file requests, just return the results
            return new_info, response, should_conclude, updated_key_findings, final_answer_prompt
    
    # If we've exhausted retries, return the last results
    return new_info, response, should_conclude, updated_key_findings, final_answer_prompt

def initialize_memory_config() -> Tuple[EmbeddingConfig, Dict[str, Any]]:
    """Initialize memory configuration from environment variables"""
    embedding_provider = os.environ.get("VECTOR_STORE_EMBEDDING_PROVIDER", "SENTENCE_TRANSFORMER")
    embedding_model_name = os.environ.get(f"VECTOR_STORE_EMBEDDING_{embedding_provider}_MODEL_NAME", "all-MiniLM-L6-v2")
    embedding_dimensionality = int(os.environ.get(f"VECTOR_STORE_EMBEDDING_{embedding_provider}_DIMENSIONALITY", 384))
    
    # Create EmbeddingConfig instance
    config = EmbeddingConfig(
        model_name=embedding_model_name,
        provider=embedding_provider,
        dimensionality=embedding_dimensionality,
        # Optional Qdrant-specific config can be handled separately
    )

    vector_store_config = {
        'qdrant': {
            'collection': os.environ.get("VECTOR_STORE_QDRANT_COLLECTION"),
            'url': os.environ.get("VECTOR_STORE_QDRANT_URL"),
            'api_key': os.environ.get("VECTOR_STORE_QDRANT_API_KEY")
        }
    }
    return config, vector_store_config

def save_conversation_to_memory(reviewer, question: str, response: str, key_findings: List[str]):
    """Save conversation results to memory"""
    if hasattr(reviewer, 'memory_manager'):
        try:
            entry_id = reviewer.memory_manager.save_memory(
                question=question,
                answer=response,
                key_findings=key_findings,
                entry_type="conversation",
                metadata={
                    "timestamp": int(time.time()),
                    "thoroughness": reviewer.target_thoroughness
                }
            )
            logger.info(f"Saved conversation to memory with ID: {entry_id}")
            return entry_id
        except Exception as e:
            logger.error(f"Failed to save conversation to memory: {str(e)}")
    return None

def cleanup_old_memories(reviewer, max_age_days: int = 30):
    """Clean up old conversation memories"""
    if hasattr(reviewer, 'memory_manager'):
        try:
            current_time = int(time.time())
            cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
            
            reviewer.memory_manager.vector_store.delete_by_filter(
                entry_type="conversation",
                older_than_timestamp=cutoff_time
            )
            logger.info(f"Cleaned up memories older than {max_age_days} days")
        except Exception as e:
            logger.error(f"Failed to clean up old memories: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--conversation-file", type=str, help="Path to conversation markdown file")
    parser.add_argument("--question", type=str, help="Direct question about the Java code")
    parser.add_argument("--thoroughness", type=int, default=6, required=False, 
                       help="Thoroughness level of the response, from 1 to 10")
    parser.add_argument("--max-rounds", type=int, default=8, required=False, 
                       help="Maximum rounds of conversation with LLM before forcing conclusion")
    parser.add_argument("--breakdown", action="store_true", 
                       help="Flag to break down the question into smaller questions")
    # Add memory-related options
    parser.add_argument("--no-memory", action="store_true",
                       help="Disable memory features for this execution")
    parser.add_argument(
        "--memory-config",
        type=str,
        help="Path to custom memory configuration file"
    )
    parser.add_argument(
        "--memory-cleanup-days",
        type=int,
        default=30,
        help="Number of days to keep memories before cleanup"
    )
    parser.add_argument(
        "--memory-similarity-threshold",
        type=float,
        default=0.6,
        help="Similarity threshold for memory retrieval (0.0-1.0)"
    )
    args = parser.parse_args()


    if args.conversation_file:
        # Process conversation file
        process_conversation_file(
            args.conversation_file,
            args.project_root,
            thoroughness=args.thoroughness,
            max_rounds=args.max_rounds
        )
    elif args.question:
        # Process direct question (existing functionality)
        root_path = os.path.abspath(args.project_root)
        if not os.path.exists(root_path):
            logger.error(f"Error: {root_path} does not exist")
            sys.exit(1)
            
        pf = ProjectFiles(repo_root_path=root_path)
        pf.from_gist_files()

        reviewer = None  # Initialize reviewer variable
        if args.breakdown:
            res, reviewer = break_down_and_answer(args.question, pf, root_path, max_rounds=args.max_rounds, thoroughness=args.thoroughness)
        else:
            res, reviewer = answer_question(pf, args.question, thoroughness=args.thoroughness, max_rounds=args.max_rounds)
            
        result_file = save_response_to_markdown(args.question, res, path=root_path+"/.gist/tell_me_about/")
        logger.info(f"Response saved to {result_file}")
        
        # Save to memory if reviewer supports it and memory is not disabled
        if reviewer and hasattr(reviewer, '_save_conversation_to_memory') and not args.no_memory:
            try:
                reviewer._save_conversation_to_memory()
                logger.info("Conversation saved to memory")
            except Exception as e:
                logger.error(f"Error saving conversation to memory: {str(e)}")
        
        # Generate state transition diagram if state tracking was used
        if reviewer and hasattr(reviewer, 'state_manager') and hasattr(reviewer.state_manager, 'conversation_history'):
            try:
                from conversation_state_machine import generate_state_transition_diagram, save_conversation_with_states
                
                # Create diagrams directory if needed
                diagrams_dir = os.path.join(root_path, ".gist", "state_diagrams")
                os.makedirs(diagrams_dir, exist_ok=True)
                
                # Generate and save diagram
                diagram = generate_state_transition_diagram(reviewer.state_manager.conversation_history)
                diagram_file = os.path.join(diagrams_dir, f"diagram_{int(time.time())}.md")
                with open(diagram_file, 'w') as f:
                    f.write("# Conversation State Diagram\n\n")
                    f.write("```mermaid\n")
                    f.write(diagram)
                    f.write("\n```\n")
                
                # Save full conversation with states
                conversation_file = os.path.join(diagrams_dir, f"conversation_{int(time.time())}.md")
                save_conversation_with_states(reviewer.state_manager.conversation_history, conversation_file)
                
                logger.info(f"Generated state transition diagram at {diagram_file}")
                logger.info(f"Saved conversation with state tracking at {conversation_file}")
            except Exception as e:
                logger.error(f"Failed to generate state transition diagram: {str(e)}")
        
        # Clean up old memories if not in test mode
        if not args.no_memory and not 'pytest' in sys.modules:
            cleanup_old_memories(reviewer)
    else:
        logger.error("Please provide either --conversation-file or --question")
        sys.exit(1)

if __name__ == "__main__":
    main()