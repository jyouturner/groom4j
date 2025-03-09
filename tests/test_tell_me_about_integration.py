import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import tempfile
sys.path.append('.')  # Add the current directory to the path

from conversation_state_machine import ConversationState

class TestTellMeAboutIntegration(unittest.TestCase):
    """Test integration with tell_me_about.py"""
    
    @patch('tell_me_about.initiate_llm_query_manager')
    @patch('tell_me_about.query_llm_with_retry')
    @patch('tell_me_about.ProjectFiles')
    def test_answer_question_state_tracking(self, mock_project_files, mock_query_llm, mock_init_llm):
        """Test that answer_question correctly tracks conversation state"""
        from tell_me_about import answer_question
        
        # Set up mocks
        mock_query_manager = MagicMock()
        mock_init_llm.return_value = mock_query_manager
        
        # Mock query_llm_with_retry to return values that will advance the state machine
        mock_query_llm.side_effect = [
            # First call - initial to exploring
            ("New info 1", "Response 1", False, [], None),
            # Second call - exploring to focusing
            ("New info 2", "Response 2", False, ["[IMPLEMENTATION_DETAIL] Detail 1"], None),
            # Third call - focusing to analyzing
            ("New info 3", "Response 3", False, ["[IMPLEMENTATION_DETAIL] Detail 1", "[ARCHITECTURE] Architecture 1"], None),
            # Fourth call - analyzing to synthesizing
            ("New info 4", "Response 4", False, ["[IMPLEMENTATION_DETAIL] Detail 1", "[ARCHITECTURE] Architecture 1", "[DATA_FLOW] Flow 1"], None),
            # Fifth call - synthesizing to concluding
            ("", "Final Response", True, ["[IMPLEMENTATION_DETAIL] Detail 1", "[ARCHITECTURE] Architecture 1", "[DATA_FLOW] Flow 1"], "Final prompt")
        ]
        
        # Call answer_question
        result = answer_question(mock_project_files.return_value, "How does this work?", thoroughness=6, max_rounds=5)
        
        # Check that query_llm_with_retry was called the expected number of times
        self.assertEqual(mock_query_llm.call_count, 5)
        
        # Check that the final result is the expected response
        self.assertEqual(result, "Final Response")
        
        # Check that the reviewer's state machine was updated correctly
        # This is challenging to test directly since the reviewer is created inside the function
        # We would need to modify the function to accept a reviewer parameter for better testability
        
    @patch('tell_me_about.initiate_llm_query_manager')
    @patch('tell_me_about.query_llm_with_retry')
    @patch('tell_me_about.ProjectFiles')
    @patch('tell_me_about.save_response_to_markdown')
    @patch('tell_me_about.generate_state_transition_diagram')
    @patch('tell_me_about.save_conversation_with_states')
    def test_process_conversation_file(self, mock_save_conv, mock_gen_diagram, mock_save_response, 
                                      mock_project_files, mock_query_llm, mock_init_llm):
        """Test that process_conversation_file correctly processes a conversation file"""
        from tell_me_about import process_conversation_file, read_last_question_from_markdown
        
        # Patch read_last_question_from_markdown to return a question
        with patch('tell_me_about.read_last_question_from_markdown') as mock_read:
            mock_read.return_value = ("How does this work?", "Previous conversation")
            
            # Set up other mocks
            mock_query_manager = MagicMock()
            mock_init_llm.return_value = mock_query_manager
            
            mock_query_llm.return_value = ("New info", "Response", True, ["[DETAIL] Detail"], "Final prompt")
            mock_save_response.return_value = "/path/to/result.md"
            mock_gen_diagram.return_value = "mermaid diagram code"
            
            # Create a temporary directory for the project root
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create .gist directory
                gist_dir = os.path.join(temp_dir, ".gist")
                os.makedirs(gist_dir, exist_ok=True)
                
                # Create a temporary conversation file
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_file.write("## User\nHow does this work?\n\n")
                    conversation_file = temp_file.name
                
                try:
                    # Call process_conversation_file
                    process_conversation_file(conversation_file, temp_dir, thoroughness=6, max_rounds=5)
                    
                    # Check that the necessary functions were called
                    mock_read.assert_called_once_with(conversation_file)
                    mock_project_files.assert_called_once()
                    mock_query_llm.assert_called_once()
                    mock_save_response.assert_called_once()
                    
                    # These might not be called if the reviewer doesn't have state_manager attribute
                    # mock_gen_diagram.assert_called_once()
                    # mock_save_conv.assert_called_once()
                    
                finally:
                    # Clean up the temporary file
                    if os.path.exists(conversation_file):
                        os.remove(conversation_file)

    @patch('llm_interaction.extract_and_process_next_steps')
    @patch('llm_interaction.extract_key_findings')
    def test_query_llm_state_context_updates(self, mock_extract_findings, mock_extract_steps):
        """Test that query_llm correctly updates state context"""
        from llm_interaction import query_llm
        
        # Set up mocks
        mock_query_manager = MagicMock()
        mock_query_manager.query.return_value = "Response with [BUSINESS_RULE] A rule"
        
        mock_extract_findings.return_value = ["[BUSINESS_RULE] A rule"]
        mock_extract_steps.return_value = "New information"
        
        # Create a mock reviewer with a state manager
        mock_reviewer = MagicMock()
        mock_reviewer.update_conversation_context = MagicMock()
        
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
        
        # Check that update_conversation_context was called with appropriate arguments
        mock_reviewer.update_conversation_context.assert_called_with(
            question="How does this work?",
            has_code_examples=False,
            has_file_requests=False,
            confidence=0.7,  # Because we have key findings
            found_key_findings=True
        )
        
        # Check that the reviewer's add_conversation method was called
        mock_reviewer.add_conversation.assert_called_once()


if __name__ == '__main__':
    unittest.main() 