import unittest
from unittest.mock import MagicMock, patch
import sys
sys.path.append('.')  # Add the current directory to the path

from conversation_state_machine import ConversationState

class TestLLMInteraction(unittest.TestCase):
    """Test LLM interaction functions"""
    
    def test_extract_key_findings(self):
        """Test extracting key findings from a response"""
        from llm_interaction import extract_key_findings
        
        # Test with a response containing key findings
        response = """
        Here's my analysis of the code.
        
        KEY_FINDINGS:
        - [BUSINESS_RULE] Authentication requires a valid JWT token
        - [IMPLEMENTATION_DETAIL] Tokens are stored in Redis with a 24-hour expiration
        - [ARCHITECTURE] The system uses a microservice architecture
        
        Let me know if you need more details.
        """
        
        findings = extract_key_findings(response)
        
        # Check that all findings were extracted
        self.assertEqual(len(findings), 3)
        self.assertIn("[BUSINESS_RULE] Authentication requires a valid JWT token", findings)
        self.assertIn("[IMPLEMENTATION_DETAIL] Tokens are stored in Redis with a 24-hour expiration", findings)
        self.assertIn("[ARCHITECTURE] The system uses a microservice architecture", findings)
        
        # Test with a response containing no key findings
        response = "Here's my analysis of the code. I didn't find any key findings."
        findings = extract_key_findings(response)
        self.assertEqual(len(findings), 0)
        
        # Test with a response containing malformed key findings
        response = """
        KEY_FINDINGS:
        - This is not properly formatted
        - [INVALID_TAG] This has an invalid tag
        - [BUSINESS_RULE] This one is valid
        """
        findings = extract_key_findings(response)
        self.assertEqual(len(findings), 1)
        self.assertIn("[BUSINESS_RULE] This one is valid", findings)
        
    def test_update_key_findings(self):
        """Test updating key findings"""
        from llm_interaction import update_key_findings
        
        # Test adding new findings
        old_findings = ["[BUSINESS_RULE] Rule 1", "[IMPLEMENTATION_DETAIL] Detail 1"]
        new_findings = ["[ARCHITECTURE] Architecture 1", "[DATA_FLOW] Flow 1"]
        
        updated = update_key_findings(old_findings, new_findings)
        
        # Check that all findings were included
        self.assertEqual(len(updated), 4)
        self.assertIn("[BUSINESS_RULE] Rule 1", updated)
        self.assertIn("[IMPLEMENTATION_DETAIL] Detail 1", updated)
        self.assertIn("[ARCHITECTURE] Architecture 1", updated)
        self.assertIn("[DATA_FLOW] Flow 1", updated)
        
        # Test with duplicate findings
        old_findings = ["[BUSINESS_RULE] Rule 1", "[IMPLEMENTATION_DETAIL] Detail 1"]
        new_findings = ["[BUSINESS_RULE] Rule 1", "[DATA_FLOW] Flow 1"]
        
        updated = update_key_findings(old_findings, new_findings)
        
        # Check that duplicates were removed
        self.assertEqual(len(updated), 3)
        self.assertEqual(updated.count("[BUSINESS_RULE] Rule 1"), 1)
        
        # Test with more than 15 findings (should be limited)
        old_findings = [f"[BUSINESS_RULE] Rule {i}" for i in range(10)]
        new_findings = [f"[IMPLEMENTATION_DETAIL] Detail {i}" for i in range(10)]
        
        updated = update_key_findings(old_findings, new_findings)
        
        # Check that the result was limited to 15 findings
        self.assertEqual(len(updated), 15)
    
    @patch('llm_interaction.extract_and_process_next_steps')
    @patch('llm_interaction.extract_key_findings')
    @patch('llm_interaction.remove_next_steps')
    def test_query_llm(self, mock_remove_next_steps, mock_extract_findings, mock_extract_steps):
        """Test the query_llm function"""
        from llm_interaction import query_llm
        
        # Set up mocks
        mock_query_manager = MagicMock()
        mock_query_manager.query.return_value = "Response with key findings"
        
        mock_extract_findings.return_value = ["[BUSINESS_RULE] A rule"]
        mock_extract_steps.return_value = "New information"
        mock_remove_next_steps.return_value = "Cleaned response"
        
        # Create a mock reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.is_history_empty.return_value = True
        mock_reviewer.should_continue_conversation.return_value = (True, None)
        
        # Call query_llm
        new_info, response, should_conclude, key_findings, final_prompt = query_llm(
            query_manager=mock_query_manager,
            question="How does this work?",
            user_prompt_template="{question} {previous_llm_response}",
            instruction_prompt="Instructions",
            function_prompt="Function prompt",
            last_response="Previous response",
            pf=None,
            iteration_number="1",
            new_information="",
            key_findings=[],
            reviewer=mock_reviewer
        )
        
        # Check that the query manager was called with the expected prompt
        mock_query_manager.query.assert_called_once()
        
        # Check that extract_key_findings was called with the response
        mock_extract_findings.assert_called_once_with("Response with key findings")
        
        # Check that extract_and_process_next_steps was called with the response
        mock_extract_steps.assert_called_once_with("Response with key findings", None)
        
        # Check that the reviewer's add_conversation method was called
        mock_reviewer.add_conversation.assert_called_once()
        
        # Check that should_continue_conversation was called
        mock_reviewer.should_continue_conversation.assert_called_once()
        
        # Check the return values
        self.assertEqual(new_info, "New information")
        self.assertEqual(response, "Cleaned response")
        self.assertEqual(should_conclude, False)
        self.assertEqual(key_findings, ["[BUSINESS_RULE] A rule"])
        self.assertIsNone(final_prompt)
    
    @patch('llm_interaction.extract_and_process_next_steps')
    def test_query_llm_with_no_new_information(self, mock_extract_steps):
        """Test query_llm when there's no new information"""
        from llm_interaction import query_llm
        
        # Set up mocks
        mock_query_manager = MagicMock()
        mock_query_manager.query.return_value = "Response with no new info"
        
        mock_extract_steps.return_value = ""  # No new information
        
        # Create a mock reviewer
        mock_reviewer = MagicMock()
        
        # Call query_llm
        new_info, response, should_conclude, key_findings, final_prompt = query_llm(
            query_manager=mock_query_manager,
            question="How does this work?",
            user_prompt_template="{question}",
            instruction_prompt="Instructions",
            function_prompt="Function prompt",
            last_response="",
            pf=None,
            iteration_number="1",
            new_information="",
            key_findings=[],
            reviewer=mock_reviewer
        )
        
        # Check that should_conclude is True when there's no new information
        self.assertEqual(new_info, "")
        self.assertTrue(should_conclude)
    
    def test_extract_and_process_next_steps(self):
        """Test extracting and processing next steps from a response"""
        from llm_interaction import extract_and_process_next_steps
        
        # Mock ProjectFiles
        mock_pf = MagicMock()
        
        # Test with file request
        response = """
        I need to look at some files to answer this question.
        
        [I need content of files: src/main/java/com/example/Main.java]
        
        This should help me understand the code better.
        """
        
        # Mock read_files to return some content
        with patch('llm_interaction.read_files') as mock_read_files:
            mock_read_files.return_value = ("File content", ["src/main/java/com/example/Main.java"], [])
            
            # Call extract_and_process_next_steps
            new_info = extract_and_process_next_steps(response, mock_pf)
            
            # Check that read_files was called with the correct file name
            mock_read_files.assert_called_once()
            self.assertEqual(mock_read_files.call_args[0][1], ["src/main/java/com/example/Main.java"])
            
            # Check that the new information contains the file content
            self.assertEqual(new_info, "File content")
        
        # Test with search request
        response = """
        I need to search for some keywords.
        
        [I need to search for keywords: <keyword>authentication</keyword>]
        
        This should help me find relevant files.
        """
        
        # Mock efficient_file_search to return some files
        with patch('llm_interaction.efficient_file_search') as mock_search:
            mock_search.return_value = ["src/main/java/com/example/Auth.java"]
            
            # Call extract_and_process_next_steps
            new_info = extract_and_process_next_steps(response, mock_pf)
            
            # Check that efficient_file_search was called with the correct keyword
            mock_search.assert_called_once_with(mock_pf.root_path, "authentication")
            
            # Check that the new information contains the search results
            self.assertIn("authentication", new_info)
            self.assertIn("Auth.java", new_info)
    
    def test_shoud_continue_conversation(self):
        """Test the shoud_continue_conversation function"""
        from llm_interaction import shoud_continue_conversation
        
        # Test with no new information
        should_continue, final_prompt = shoud_continue_conversation(
            "How does this work?",
            "Response",
            "",  # No new information
            None  # No reviewer
        )
        
        # Should not continue when there's no new information
        self.assertFalse(should_continue)
        self.assertIsNone(final_prompt)
        
        # Test with new information but no reviewer
        should_continue, final_prompt = shoud_continue_conversation(
            "How does this work?",
            "Response",
            "New information",
            None  # No reviewer
        )
        
        # Should continue when there's new information
        self.assertTrue(should_continue)
        self.assertIsNone(final_prompt)
        
        # Test with new information and reviewer
        mock_reviewer = MagicMock()
        mock_reviewer.is_history_empty.return_value = True
        mock_reviewer.should_continue_conversation.return_value = (False, "Final prompt")
        
        should_continue, final_prompt = shoud_continue_conversation(
            "How does this work?",
            "Response",
            "New information",
            mock_reviewer,
            True  # Check history
        )
        
        # Should respect reviewer's decision
        self.assertFalse(should_continue)
        self.assertEqual(final_prompt, "Final prompt")
        
        # Check that reviewer methods were called
        mock_reviewer.add_conversation.assert_called_once()
        mock_reviewer.should_continue_conversation.assert_called_once()


if __name__ == '__main__':
    unittest.main() 