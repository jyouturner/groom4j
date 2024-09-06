from typing import Tuple, List, Optional
import logging

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

You are an AI assistant tasked with reviewing a conversation between a human and an AI about a Java project analysis. Your goal is to determine if the conversation is progressing effectively or if it's at risk of entering an infinite loop.

Below is a summary of the conversation so far:

{conversation_summary}

===

Please analyze this conversation and answer the following questions:

1. Is the conversation making progress towards answering the main question? Why or why not?

2. Are there any signs that the AI is stuck or repeating itself unnecessarily?

3. Based on the information gathered so far, does it seem like the AI has enough information to answer the main question? If not, what crucial information is still missing?

4. What action do you recommend for the next step? Choose one of the following and explain why:
   a) Continue the conversation as is
   b) Push for a conclusion by removing the option to request more information



Your analysis will be used to guide the conversation and ensure it reaches a productive conclusion. Be concise but thorough in your responses.

After your analysis, please provide a final recommendation in the following format:

RECOMMENDATION: [CONTINUE|CONCLUDE]
REASON: [Brief explanation for the recommendation]
EFFICIENCY_SCORE: [1-10]


If your recommendation is CONCLUDE, please provide:
FINAL_ANSWER_PROMPT: [A concise prompt to give the main LLM to formulate its final answer]

Explanation of recommendations:
- CONTINUE: The conversation is progressing well and should continue as is.
- CONCLUDE: There's sufficient information to answer the question. The main LLM should provide a final answer.

Please ensure your recommendation is followed by the appropriate additional information as specified above.
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

    def __init__(self, query_manager, max_history=10):
        self.query_manager = query_manager
        self.conversation_list = []
        self.max_history = max_history

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
    def review_conversation(self) -> Tuple[str, int, List[str], Optional[str]]:
        conversation_summary_str = ""
        for i, round_data in enumerate(self.conversation_list, 1):
            conversation_summary_str += f"Round {i}:\n"
            conversation_summary_str += f"Human: {round_data['human']}\n"
            conversation_summary_str += f"AI: {round_data['ai']}\n\n"

        # Query the LLM to get the review
        review_prompt = review_prompt_template.format(conversation_summary=conversation_summary_str)
        
        try:
            review_response = self.query_manager.query(review_prompt)
                
            # Log the review prompt and response using langfuse
            try:
                logger.debug("Logging review prompt and response to langfuse")

            except Exception as e:
                logger.warning(f"Failed to log to langfuse: {str(e)}")

        except Exception as e:
            logger.error(f"Error querying LLM for review: {str(e)}", exc_info=True)
            return "CONTINUE", None, [], None

        return self.process_llm_response(review_response)

    def process_llm_response(self, reviewer_response):
        import re

        # Initialize variables with default values
        recommendation = None
        efficiency_score = None
        next_steps = []
        final_answer_prompt = None

        # Print the full reviewer response for debugging
        logger.debug("Full reviewer response:")
        logger.debug(reviewer_response)

        # Extract recommendation
        recommendation_match = re.search(r'RECOMMENDATION:\s*(\w+)', reviewer_response, re.IGNORECASE)
        if recommendation_match:
            recommendation = recommendation_match.group(1)
        else:
            logger.warning("No recommendation found in reviewer response")
            recommendation = "CONTINUE"  # Default to continue if no recommendation is found

        # Extract efficiency score
        efficiency_match = re.search(r'EFFICIENCY_SCORE:\s*(\d+)', reviewer_response, re.IGNORECASE)
        efficiency_score = int(efficiency_match.group(1)) if efficiency_match else None

        # Process based on recommendation
        if recommendation in ["CONTINUE", "REDIRECT"]:
            next_steps_match = re.search(r'NEXT_STEPS:\s*(.+)', reviewer_response, re.IGNORECASE | re.DOTALL)
            next_steps = next_steps_match.group(1).split(', ') if next_steps_match else []
        elif recommendation == "CONCLUDE":
            final_answer_prompt_match = re.search(r'FINAL_ANSWER_PROMPT:\s*(.+)', reviewer_response, re.IGNORECASE | re.DOTALL)
            final_answer_prompt = final_answer_prompt_match.group(1) if final_answer_prompt_match else None
        elif recommendation == "RESTART":
            # Logic to restart the conversation
            pass

        logger.info(f"Processed response: Recommendation={recommendation}, Efficiency={efficiency_score}, Next steps={next_steps}, Final prompt={final_answer_prompt}")

        return recommendation, efficiency_score, next_steps, final_answer_prompt

    def should_continue_conversation(self) -> bool:
        recommendation, efficiency_score, next_steps, final_answer_prompt = self.review_conversation()
        
        if recommendation == "CONTINUE":
            return True
        elif recommendation == "REDIRECT":
            # Implement logic to incorporate next_steps into the next prompt
            self.incorporate_next_steps(next_steps)
            return False
        elif recommendation == "CONCLUDE":
            # Implement logic to use final_answer_prompt
            self.get_final_answer(final_answer_prompt)
            return False
        elif recommendation == "RESTART":
            self.restart_conversation()
            return False
        else:
            raise ValueError(f"Unknown recommendation: {recommendation}")

    def incorporate_next_steps(self, next_steps: List[str]):
        # Implement logic to incorporate next_steps into the next prompt
        pass

    def get_final_answer(self, final_answer_prompt: str):
        # Implement logic to get the final answer using the provided prompt
        pass

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