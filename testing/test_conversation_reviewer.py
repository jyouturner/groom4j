import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import List, Tuple, Optional
from mock_llm_router import mock_llm_query_manager, mock_llm_factory
from conversation_reviewer import ConversationReviewer, LLMQueryManager  # Import your actual classes

use_llm = "gemini"
LLMQueryManager = None
class TestConversationReviewer(unittest.TestCase):

    def setUp(self):
        from config_utils import load_config_to_env
        load_config_to_env(config_path="testing/application_test.yml")

        global LLMQueryManager
        with mock_llm_query_manager():
            from llm_client import LLMQueryManager
            yield
       
        self.reviewer = ConversationReviewer(query_manager)

    def test_conversation_review(self):
        # Simulate a conversation
        conversations = [
            ("What database technology is used in the project, and how is the connection to the database established?", 
             "To answer this question, I'll need to investigate the project structure and look for configuration files related to database connections. Let me start by searching for relevant keywords."),
            ("New information provided:\n- Searches: [database, connection, MongoDB, Redis]\n- File contents: [application.properties, MongoConfig.java, RedisConfig.java]\n- Package info: [com.example.config]",
             "Based on the search results and file contents, it appears that this project uses both MongoDB and Redis. I've found configuration files for both databases. To provide a more detailed answer, I'd like to examine the contents of MongoConfig.java and RedisConfig.java."),
            ("New information provided:\n- File contents: [MongoConfig.java, RedisConfig.java]",
             "After analyzing MongoConfig.java and RedisConfig.java, I can confirm that the project uses both MongoDB and Redis. MongoDB seems to be the primary database, while Redis is likely used for caching. The connections are established using Spring Boot's auto-configuration with custom configuration classes. To provide a complete answer, I'd like to check for any environment variables or application properties that might contain connection details.")
        ]

        # Add conversations to the reviewer
        for human, ai in conversations:
            self.reviewer.add_conversation(human, ai)

        # Get the review
        recommendation, efficiency_score, next_steps, final_answer_prompt = self.reviewer.review_conversation()

        # Assertions
        self.assertIn(recommendation, ["CONTINUE", "CONCLUDE", "REDIRECT", "RESTART"])
        self.assertIsInstance(efficiency_score, int)
        self.assertTrue(1 <= efficiency_score <= 10)

        if recommendation in ["CONTINUE", "REDIRECT"]:
            self.assertIsInstance(next_steps, list)
            self.assertTrue(len(next_steps) > 0)
        elif recommendation == "CONCLUDE":
            self.assertIsNotNone(final_answer_prompt)
            self.assertIsInstance(final_answer_prompt, str)

    def test_should_continue_conversation(self):
        # Similar setup as above
        conversations = [
            # ... (same conversations as above)
        ]

        for human, ai in conversations:
            self.reviewer.add_conversation(human, ai)

        # Test the should_continue_conversation method
        should_continue = self.reviewer.should_continue_conversation()

        # Assert based on the expected behavior
        self.assertIsInstance(should_continue, bool)

if __name__ == '__main__':
    unittest.main()