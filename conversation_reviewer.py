from typing import Tuple, List, Optional
import logging
import re

# the order of the following imports is important
# since the initialization of langfuse depends on the os environment variables
# which are loaded in the config_utils module
from config_utils import load_config_to_env
load_config_to_env()
from llm_client import LLMQueryManager, langfuse_context, observe

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

    def __init__(self, query_manager, target_thoroughness=6, max_history=10, max_rounds=8):
        """
        Initialize the ConversationReviewer
        Args:
            query_manager: The LLM query manager to use for reviews
            target_thoroughness (int): Target thoroughness level (1-10)
            max_history (int): Maximum conversation history to maintain
            max_rounds (int): Maximum number of conversation rounds before forcing conclusion
        """
        self.query_manager = query_manager
        self.conversation_list = []
        self.max_history = max_history
        self.target_thoroughness = min(max(1, target_thoroughness), 10)
        self.max_rounds = max_rounds
        self.current_round = 0
        self.consecutive_empty_rounds = 0
        self.max_empty_rounds = 3

    def is_history_empty(self):
        return len(self.conversation_list) == 0

    def add_conversation(self, human: str, ai: str):
        conversation = {
            "human": human,
            "ai": ai
        }
        self.conversation_list.append(conversation)
        
        # Limit the conversation history to max_history entries
        if len(self.conversation_list) > self.max_history:
            self.conversation_list = self.conversation_list[-self.max_history:]
        
        # Debug print
        logger.debug(f"Added conversation:")
        logger.debug(f"Human: {human[:50]}...")
        logger.debug(f"AI: {ai[:50]}...")
        logger.debug(f"Conversation history length: {len(self.conversation_list)}")

    
    @observe(name="review_conversation", capture_input=True, capture_output=True)
    def review_conversation(self) -> Tuple[str, Optional[str]]:
        """Review the conversation and provide guidance."""
        # Don't try to review empty conversations
        if not self.conversation_list:
            logger.info("No conversation to review yet")
            return "CONTINUE", None

        conversation_summary_str = ""
        for i, round_data in enumerate(self.conversation_list, 1):
            conversation_summary_str += f"Round {i}:\n"
            conversation_summary_str += f"Human: {round_data['human']}\n"
            conversation_summary_str += f"AI: {round_data['ai']}\n\n"

        # Query the LLM to get the review
        review_prompt = review_prompt_template.format(target_throughness=self.target_thoroughness)
        
        try:
            review_response = self.query_manager.query(review_prompt)
            return self.process_llm_response(review_response)
        except Exception as e:
            logger.error(f"Error querying LLM for review: {str(e)}", exc_info=True)
            return "CONTINUE", None

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
        
        return min(10, score)

    def process_llm_response(self, reviewer_response) -> Tuple[str, Optional[str]]:
        """Process the reviewer LLM's response to determine next steps."""
        # Extract recommendation and thoroughness from reviewer's response
        recommendation_match = re.search(r'RECOMMENDATION:\s*(CONTINUE|CONCLUDE)', reviewer_response)
        thoroughness_match = re.search(r'THOROUGHNESS_SCORE:\s*(\d+)', reviewer_response)
        
        recommendation = recommendation_match.group(1) if recommendation_match else "CONTINUE"
        thoroughness_score = int(thoroughness_match.group(1)) if thoroughness_match else 1
        
        logger.info(f"Reviewer assessment - Recommendation: {recommendation}, Thoroughness: {thoroughness_score}/10")
        
        # Check for empty rounds - only if we have conversation history
        if self.conversation_list:
            if not self._has_new_content(self.conversation_list[-1]['ai']):
                self.consecutive_empty_rounds += 1
                logger.info(f"No new content detected. Empty rounds: {self.consecutive_empty_rounds}/{self.max_empty_rounds}")
            else:
                self.consecutive_empty_rounds = 0
            
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

    def should_continue_conversation(self) -> Tuple[bool, Optional[str]]:
        # Check if we've exceeded max rounds
        self.current_round += 1
        if self.current_round >= self.max_rounds:
            logger.info(f"Reached maximum rounds ({self.max_rounds}), forcing conclusion")
            return False, "Please provide a final comprehensive answer based on all information gathered so far."
            
        # Continue with existing review logic
        recommendation, final_answer_prompt = self.review_conversation()
        
        # Log the decision process
        logger.info(f"Round {self.current_round}/{self.max_rounds}")
        logger.info(f"Recommendation: {recommendation}")
        logger.info(f"Target thoroughness: {self.target_thoroughness}")
        
        return recommendation == "CONTINUE", final_answer_prompt

    def incorporate_next_steps(self, next_steps: List[str]):
        # Implement logic to incorporate next_steps into the next prompt
        pass

    def get_final_answer(self, final_answer_prompt: str):
        # Implement logic to get the final answer using the provided prompt
        return final_answer_prompt

    def restart_conversation(self):
        pass


if __name__ == "__main__":
    # test the conversation reviewer in a simple way but real way
    reviewer = ConversationReviewer(query_manager=LLMQueryManager(use_llm="anthropic", tier="tier2", system_prompt="You are an AI assistant to review the conversation between a human and an AI about a Java project analysis."))
    reviewer.add_conversation("What is the main purpose of this project?", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    reviewer.add_conversation("", "The main purpose of this project is to analyze Java projects.")
    res = reviewer.should_continue_conversation()
    print(res)