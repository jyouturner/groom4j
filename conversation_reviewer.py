
import logging
import re
from memory.memory_manager import MemoryManager
import os
from pathlib import Path

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()
from llm_client import LLMQueryManager, langfuse_context, observe

# Import the state machine
from conversation_state_machine import (
    ConversationState, 
    ConversationStateMachine,
    StateManager,
    generate_prompt_for_state
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

review_prompt_template = """
Please analyze this conversation and answer the following questions:

1. Is the conversation making progress towards answering the main question?
2. Are there any signs that the AI is stuck or repeating itself unnecessarily?
3. If crucial information is still missing, what specific details are needed?
4. Evaluate the potential value of continuing the conversation versus concluding it now

Interms of **THOROUGHNESS**, please ensure the conversation should continue until the **THOROUGHNESS** is {target_throughness} of 10.

RECOMMENDATION: [CONTINUE|CONCLUDE]
THOROUGHNESS_SCORE: [1-10, where 10 indicates extremely thorough]
"""


#
#Round 1:
#
#Human: Original Question or Promot
#
#AI: response
#
#Round 2:
#
#Human: New information provided:
#- Searches: [keyword1], [keyword2], [keyword3]
#- File contents: [filename1], [filename2], [filename3]
#- Package info: [package1], [package2]
#
#AI: response
#...


class ConversationReviewer:

    def __init__(self, query_manager, target_thoroughness=6, max_history=10, max_rounds=8, use_memory=True):
        """
        Initialize the ConversationReviewer with memory support
        Args:
            query_manager: The LLM query manager to use for reviews
            target_thoroughness (int): Target thoroughness level (1-10)
            max_history (int): Maximum conversation history to maintain
            max_rounds (int): Maximum number of conversation rounds before forcing conclusion
            use_memory (bool): Whether to use persistent memory
        """
        self.query_manager = query_manager
        self.conversation_list = []
        self.max_history = max_history
        self.target_thoroughness = min(max(1, target_thoroughness), 10)
        self.max_rounds = max_rounds
        self.current_round = 0
        self.consecutive_empty_rounds = 0
        self.max_empty_rounds = 3
        
        # Initialize the state machine
        self.state_manager = StateManager()
        self.conversation_context = {}
        
        # Initialize memory manager if enabled
        self.use_memory = use_memory
        self.memory_manager = None
        self.current_question = None
        self.current_answer = None
        self.current_key_findings = []
        self.files_accessed = []

    def initialize_memory(self, project_root):
        """Initialize memory manager with project information"""
        if self.use_memory:
            try:
                # Ensure project_root is absolute
                if project_root:
                    project_root = os.path.abspath(project_root)
                else:
                    project_root = os.getcwd()
                
                # Initialize memory manager
                self.memory_manager = MemoryManager(project_root=project_root)
                logger.info(f"Initialized memory manager for project {self.memory_manager.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {str(e)}")
                self.use_memory = False

    def is_history_empty(self):
        return len(self.conversation_list) == 0

    def add_conversation(self, human: str, ai: str):
        """
        Add a conversation turn to the history
        Args:
            human: Human message
            ai: AI response
        """
        conversation = {
            "human": human,
            "ai": ai
        }
        self.conversation_list.append(conversation)
        
        # Set current question/answer for memory storage
        if not self.current_question and human:
            self.current_question = human
        self.current_answer = ai
        
        # Track accessed files for memory context
        self._track_accessed_files(human)
        self._track_accessed_files(ai)
        
        # Extract and track key findings
        self._extract_key_findings(ai)
        
        # Limit the conversation history to max_history entries
        if len(self.conversation_list) > self.max_history:
            self.conversation_list = self.conversation_list[-self.max_history:]
        
        # Update state manager conversation history
        self.state_manager.update_conversation_history("user", human)
        self.state_manager.update_conversation_history("assistant", ai)
        
        # Debug print
        logger.debug(f"Added conversation:")
        logger.debug(f"Human: {human[:50]}...")
        logger.debug(f"AI: {ai[:50]}...")
        logger.debug(f"Conversation history length: {len(self.conversation_list)}")
    
    def _track_accessed_files(self, text):
        """Extract accessed file names from text"""
        if not text:
            return
            
        # Extract file paths from content access requests
        file_request_pattern = r"\[I need content of files:(.*?)\]"
        file_requests = re.findall(file_request_pattern, text, re.DOTALL)
        
        for request in file_requests:
            # Extract file names (might be comma-separated)
            files = re.findall(r"<file>(.*?)</file>", request)
            if not files:
                # Try extracting comma-separated file names
                files = [f.strip() for f in request.split(",")]
            
            self.files_accessed.extend(files)
    
    def _extract_key_findings(self, text):
        """Extract key findings from AI response"""
        if not text:
            return
            
        # Look for key findings section
        key_findings_pattern = r"KEY_FINDINGS:(.+?)(?:\n\n|\Z)"
        findings_match = re.search(key_findings_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if findings_match:
            findings_text = findings_match.group(1)
            # Extract individual findings (lines starting with - or *)
            findings = re.findall(r"[-*]\s*\[(.*?)\](.*?)(?:\n|$)", findings_text)
            
            for finding_type, finding_text in findings:
                finding = f"[{finding_type}]{finding_text.strip()}"
                if finding not in self.current_key_findings:
                    self.current_key_findings.append(finding)

    def get_current_state(self) -> ConversationState:
        """Get the current conversation state"""
        return self.state_manager.state_machine.current_state
    
    def get_state_prompt_guidance(self) -> str:
        """Get prompt guidance based on current state"""
        result = self.state_manager.state_machine.process(self.conversation_context)
        return result.get("prompt_guidance", "")
    
    def update_conversation_context(self, **kwargs):
        """Update the conversation context used by the state machine"""
        self.conversation_context.update(kwargs)
        
        # Always update round information
        self.conversation_context["round"] = self.current_round
        self.conversation_context["max_rounds"] = self.max_rounds
    
    @observe(name="review_conversation", capture_input=True, capture_output=True)
    def review_conversation(self) -> Tuple[str, Optional[str]]:
        """Review the conversation and provide guidance."""
        # Call the original method to get the recommendation
        recommendation, final_answer_prompt = self._original_review_conversation()
        
        # If we're concluding the conversation, save to memory
        if recommendation == "CONCLUDE" and self.use_memory and self.memory_manager:
            self._save_conversation_to_memory()
        
        return recommendation, final_answer_prompt
    
    def _original_review_conversation(self) -> Tuple[str, Optional[str]]:
        """Original review_conversation method (rename the existing method to this)"""
        # Don't try to review empty conversations
        if not self.conversation_list:
            logger.info("No conversation to review yet")
            return "CONTINUE", None

        # Update conversation context with latest information
        self.update_conversation_context(
            relevant_components_found=(self.current_round > 0),
            components_selected=(self.current_round > 1)
        )
        
        # Process through state machine
        old_state = self.state_manager.state_machine.current_state
        state_result = self.state_manager.state_machine.process(self.conversation_context)
        new_state = self.state_manager.state_machine.current_state
        
        if old_state != new_state:
            self.state_manager.log_state_transition(
                old_state, 
                new_state, 
                f"Round {self.current_round} transition"
            )
            
        # Get thoroughness target adjusted for current state
        state_thoroughness = self.state_manager.get_thoroughness_target_for_state(new_state)
        adjusted_thoroughness = min(self.target_thoroughness, state_thoroughness)
        
        # Prepare conversation summary for review
        conversation_summary_str = ""
        for i, round_data in enumerate(self.conversation_list, 1):
            conversation_summary_str += f"Round {i}:\n"
            conversation_summary_str += f"Human: {round_data['human']}\n"
            conversation_summary_str += f"AI: {round_data['ai']}\n\n"

        # Query the LLM to get the review
        review_prompt = review_prompt_template.format(target_throughness=adjusted_thoroughness)
        
        try:
            review_response = self.query_manager.query(review_prompt)
            recommendation, final_answer_prompt = self.process_llm_response(review_response)
            
            # Add state-specific guidance if we need to continue
            if recommendation == "CONTINUE" and final_answer_prompt is None:
                state_guidance = state_result.get("prompt_guidance", "")
                if state_guidance:
                    logger.info(f"Adding state-specific guidance: {state_guidance}")
                    # We'll keep the recommendation but add state-specific guidance
                    
            # Special handling for certain states
            if new_state == ConversationState.CONCLUDING:
                recommendation = "CONCLUDE"
                if not final_answer_prompt:
                    final_answer_prompt = self._generate_concluding_prompt()
            
            logger.info(f"Conversation state: {new_state.value}")
            return recommendation, final_answer_prompt
            
        except Exception as e:
            logger.error(f"Error querying LLM for review: {str(e)}", exc_info=True)
            return "CONTINUE", None
    
    def _save_conversation_to_memory(self):
        """Save the current conversation to memory"""
        if not self.current_question or not self.current_answer:
            logger.warning("No conversation to save to memory")
            return
            
        try:
            if self.memory_manager:
                # Save memory entry
                entry_id = self.memory_manager.save_memory(
                    question=self.current_question,
                    answer=self.current_answer,
                    key_findings=self.current_key_findings,
                    files_accessed=list(set(self.files_accessed)),  # Deduplicate
                    entry_type="conversation",
                    metadata={
                        "thoroughness": self.conversation_context.get("current_thoroughness", 0),
                        "state_path": [s.value for s in self.state_manager.state_machine.state_history]
                    }
                )
                
                if entry_id:
                    logger.info(f"Saved conversation to memory with ID: {entry_id}")
                else:
                    logger.warning("Failed to save conversation to memory")
        except Exception as e:
            logger.error(f"Error saving conversation to memory: {str(e)}")
    
    def get_relevant_memories(self, question: str) -> str:
        """Get relevant memories for the provided question"""
        if not self.use_memory or not self.memory_manager:
            return ""
            
        try:
            context = self.memory_manager.get_relevant_context(
                query=question,
                limit=3,
                score_threshold=0.75
            )
            
            if context:
                logger.info(f"Found relevant memories: {len(context.split('---'))}")
                return context
        except Exception as e:
            logger.error(f"Error getting relevant memories: {str(e)}")
            
        return ""

    def _evaluate_thoroughness(self, response: str) -> int:
        """
        Evaluate the thoroughness of a response based on multiple factors and context.
        Returns a score from 1-10.
        """
        score = 3  # Base score for a well-formed response
        
        # Count key findings by type
        findings = {
            'BUSINESS_RULE': 0,
            'IMPLEMENTATION_DETAIL': 0,
            'ARCHITECTURE': 0,
            'DATA_FLOW': 0,
            'SPECIAL_CASE': 0
        }
        
        for tag in findings.keys():
            findings[tag] = len(re.findall(f'\\[{tag}\\]', response))
        
        # Score based on findings - any findings are good
        if sum(findings.values()) > 0:
            score += 2  # Points for having any findings
            # Bonus point for multiple types of findings
            if sum(1 for count in findings.values() if count > 0) > 1:
                score += 1
        
        # Check for code examples or file references
        code_matches = re.findall(r'```(?:java|xml|properties|markdown)(.*?)```', response, re.DOTALL)
        if code_matches:
            score += 1
            # Bonus for multiple relevant code examples
            if len(code_matches) > 1:
                score += 1
        
        # Check for structured explanation
        has_structure = False
        if len(re.findall(r'^##? ', response, re.MULTILINE)) > 1:  # Has sections
            score += 1
            has_structure = True
        
        # Check for technical depth
        technical_terms = re.findall(r'\b(class|method|interface|implementation|configuration|property|parameter|value|option|setting)\b', 
                                   response, re.IGNORECASE)
        if len(set(technical_terms)) >= 3:
            score += 1
        
        # Check for completeness indicators
        completeness_indicators = [
            re.search(r'(limitations?|restrictions?|constraints?)', response, re.IGNORECASE) is not None,
            re.search(r'(example|for instance|such as)', response, re.IGNORECASE) is not None,
            re.search(r'(note|important|key point)', response, re.IGNORECASE) is not None
        ]
        score += sum(completeness_indicators)
        
        logger.info(f"""Thoroughness evaluation:
            - Findings: {findings}
            - Code examples: {len(code_matches)}
            - Has structure: {has_structure}
            - Technical terms: {len(set(technical_terms))}
            - Completeness indicators: {sum(completeness_indicators)}
            - Final score: {min(10, score)}
        """)
        
        # Update the conversation context with the thoroughness score
        self.update_conversation_context(current_thoroughness=min(10, score))
        
        return min(10, score)

    def process_llm_response(self, reviewer_response) -> Tuple[str, Optional[str]]:
        """Process the reviewer LLM's response to determine next steps."""
        # Extract recommendation and thoroughness from reviewer's response
        recommendation_match = re.search(r'RECOMMENDATION:\s*(CONTINUE|CONCLUDE)', reviewer_response)
        thoroughness_match = re.search(r'THOROUGHNESS_SCORE:\s*(\d+)', reviewer_response)
        
        recommendation = recommendation_match.group(1) if recommendation_match else "CONTINUE"
        thoroughness_score = int(thoroughness_match.group(1)) if thoroughness_match else 1
        
        logger.info(f"Reviewer assessment - Recommendation: {recommendation}, Thoroughness: {thoroughness_score}/10")
        
        # Update conversation context with the thoroughness score
        self.update_conversation_context(current_thoroughness=thoroughness_score)
        
        # Check for empty rounds - only if we have conversation history
        if self.conversation_list:
            if not self._has_new_content(self.conversation_list[-1]['ai']):
                self.consecutive_empty_rounds += 1
                logger.info(f"No new content detected. Empty rounds: {self.consecutive_empty_rounds}/{self.max_empty_rounds}")
                
                # Update context to potentially trigger RECOVERY state
                if self.consecutive_empty_rounds >= 2:
                    self.update_conversation_context(error_detected=True)
            else:
                self.consecutive_empty_rounds = 0
                self.update_conversation_context(error_detected=False)
            
            # If stuck, provide guidance
            if self.consecutive_empty_rounds >= self.max_empty_rounds:
                logger.info("Detected conversation is stuck. Providing guidance for new directions.")
                return "CONCLUDE", self._generate_guidance_prompt(thoroughness_score)

        # Trust the reviewer's thoroughness assessment
        if thoroughness_score >= self.target_thoroughness:
            logger.info(f"Reached target thoroughness ({thoroughness_score} >= {self.target_thoroughness})")
            return "CONCLUDE", None
        
        logger.info(f"Current thoroughness ({thoroughness_score}) is below target ({self.target_thoroughness})")
        return recommendation, None

    def _has_new_content(self, response: str) -> bool:
        """Check if the response contains substantive new content."""
        # Look for key indicators of progress
        has_findings = "[" in response and "]" in response
        has_code = "```" in response
        has_file_requests = any(x in response for x in ["[I need to search", "[I need content of files:", "[I need info about packages:"])
        has_structure = len(re.findall(r'^##? ', response, re.MULTILINE)) > 1
        
        # Check for specific content patterns that indicate progress
        has_specific_findings = re.search(r'\[(BUSINESS_RULE|IMPLEMENTATION_DETAIL|DATA_FLOW|ARCHITECTURE|SPECIAL_CASE)\]', response) is not None
        has_file_analysis = re.search(r'(file|files) (contains?|defines?|specifies?|sets?|configures?)', response, re.IGNORECASE) is not None
        
        return has_specific_findings or has_file_analysis or has_code or has_file_requests or has_structure

    def _generate_guidance_prompt(self, current_thoroughness: int) -> str:
        """Generate a prompt to guide the LLM to a conclusion."""
        # Check the current state and customize the guidance accordingly
        current_state = self.state_manager.state_machine.current_state
        
        # Generate the appropriate state-specific prompt
        if current_state in [ConversationState.SYNTHESIZING, ConversationState.CONCLUDING]:
            return generate_prompt_for_state(current_state, {
                "question": self._get_original_question(),
                "current_thoroughness": current_thoroughness,
                "rounds_remaining": self.max_rounds - self.current_round,
                "key_findings": self._extract_key_findings_from_history()
            })
        else:
            # Default concluding guidance
            return f"""
Based on the current analysis (thoroughness score: {current_thoroughness}/10), please provide a final comprehensive answer that:

1. Synthesizes all the information gathered so far
2. Clearly states what is known with confidence
3. Identifies any remaining uncertainties or gaps
4. Makes reasonable assumptions where information is missing
5. Suggests what aspects would need further investigation

Focus on providing actionable insights from the information we have, rather than continuing to search for new information.

Format your response with:
- Clear section headings
- Code examples where relevant
- Key findings tagged appropriately
- A "Limitations and Future Investigation" section
"""

    def _generate_concluding_prompt(self) -> str:
        """Enhanced concluding prompt generation with memory"""
        base_prompt = generate_prompt_for_state(ConversationState.CONCLUDING, {
            "question": self._get_original_question(),
            "current_thoroughness": self.conversation_context.get("current_thoroughness", 5),
            "rounds_remaining": 0,
            "key_findings": self._extract_key_findings_from_history(),
            "conclusions": self._extract_conclusions_from_history()
        })
        
        # Add memory context if available
        if self.use_memory and self.conversation_context.get("memories_context"):
            memory_context = self.conversation_context.get("memories_context")
            memory_addition = f"\n\nConsider these relevant memories from previous conversations:\n{memory_context}\n\n"
            base_prompt = memory_addition + base_prompt
        
        return base_prompt
    
    def _get_original_question(self) -> str:
        """Get the original question from the conversation history"""
        if self.conversation_list:
            return self.conversation_list[0].get("human", "")
        return ""
    
    def _extract_key_findings_from_history(self) -> List[str]:
        """Extract key findings from conversation history"""
        key_findings = []
        for conv in self.conversation_list:
            ai_response = conv.get("ai", "")
            # Use a regex to extract key findings from the response
            findings_section = re.search(r'KEY_FINDINGS:(.*?)(?=\n\n|\Z)', ai_response, re.DOTALL | re.IGNORECASE)
            if findings_section:
                findings = findings_section.group(1).strip().split('\n')
                for finding in findings:
                    if finding.strip() and "[" in finding and "]" in finding:
                        key_findings.append(finding.strip())
        return key_findings
    
    def _extract_conclusions_from_history(self) -> List[str]:
        """Extract conclusions from conversation history"""
        conclusions = []
        for conv in self.conversation_list:
            ai_response = conv.get("ai", "")
            # Look for conclusions or summaries
            conclusion_sections = re.findall(r'(?:##\s*Conclusion|##\s*Summary)(.*?)(?=\n##|\Z)', 
                                            ai_response, re.DOTALL | re.IGNORECASE)
            for section in conclusion_sections:
                points = section.strip().split('\n')
                for point in points:
                    if point.strip() and len(point.strip()) > 20:  # Avoid very short lines
                        conclusions.append(point.strip())
        return conclusions

    def should_continue_conversation(self) -> Tuple[bool, Optional[str]]:
        """
        Enhanced should_continue_conversation method that considers memory
        Returns: (should_continue, final_answer_prompt)
        """
        # Check if we've exceeded max rounds
        self.current_round += 1
        self.update_conversation_context(round=self.current_round)
        
        if self.current_round >= self.max_rounds:
            logger.info(f"Reached maximum rounds ({self.max_rounds}), forcing conclusion")
            self.state_manager.state_machine.current_state = ConversationState.CONCLUDING
            final_answer_prompt = self._generate_concluding_prompt()
            return False, final_answer_prompt
            
        # Check if the current question has relevant memories
        if (self.use_memory and self.memory_manager and self.current_question 
                and self.current_round == 1):  # Only on first round
            memories_context = self.get_relevant_memories(self.current_question)
            if memories_context:
                # Update conversation context with memory information
                self.update_conversation_context(
                    relevant_memories_found=True,
                    memories_context=memories_context
                )
        
        # Continue with existing review logic enhanced with memory
        recommendation, final_answer_prompt = self.review_conversation()
        
        # If concluding and we have memory, enhance the final prompt
        if recommendation != "CONTINUE" and self.use_memory and final_answer_prompt:
            # Add memory context to final answer prompt if available
            memories_context = self.conversation_context.get("memories_context", "")
            if memories_context:
                memory_addition = f"\n\nConsider these relevant memories from previous conversations:\n{memories_context}\n\n"
                final_answer_prompt = memory_addition + final_answer_prompt
        
        # Generate state-specific final prompt if concluding
        if recommendation != "CONTINUE" and self.state_manager.state_machine.current_state != ConversationState.CONCLUDING:
            self.state_manager.state_machine.current_state = ConversationState.CONCLUDING
            if not final_answer_prompt:
                final_answer_prompt = self._generate_concluding_prompt()
        
        return recommendation == "CONTINUE", final_answer_prompt

    def incorporate_next_steps(self, next_steps: List[str]):
        # Implement logic to incorporate next_steps into the next prompt
        pass

    def get_final_answer(self, final_answer_prompt: str):
        # Implement logic to get the final answer using the provided prompt
        return final_answer_prompt

    def restart_conversation(self):
        self.conversation_list = []
        self.current_round = 0
        self.consecutive_empty_rounds = 0
        self.conversation_context = {}
        self.state_manager = StateManager()  # Reinitialize the state manager
    
    def save_state(self, path: str):
        """Save the current conversation state to disk"""
        self.state_manager.persist_session(path)
    
    def load_state(self, path: str) -> bool:
        """Load conversation state from disk"""
        return self.state_manager.restore_session(path)


if __name__ == "__main__":
    # test the conversation reviewer in a simple way but real way
    reviewer = ConversationReviewer(query_manager=LLMQueryManager(use_llm="anthropic", tier="tier2", system_prompt="You are an AI assistant to review the conversation between a human and an AI about a Java project analysis."))
    reviewer.add_conversation("What is the main purpose of this project?", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    res = reviewer.should_continue_conversation()
    print(res)