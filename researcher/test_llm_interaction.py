import unittest
from unittest.mock import Mock, patch
from .llm_interaction import extract_and_process_next_steps


class TestLLMInteraction(unittest.TestCase):
    def setUp(self):
        # Create a mock ProjectFiles object
        self.mock_pf = Mock()
        
        # Mock the read_files function to return predictable results
        self.mock_read_files_patcher = patch('llm_interaction.read_files')
        self.mock_read_files = self.mock_read_files_patcher.start()
        
        # Default mock return values
        self.mock_read_files.return_value = (
            "mock file contents",  # file_contents
            ["file1.java"],       # files_found
            []                    # files_not_found
        )

    def tearDown(self):
        self.mock_read_files_patcher.stop()

    def test_simple_file_request(self):
        response = """Here's what I found.
        
        **Next Steps**
        [I need content of files: path/to/file1.java]
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        self.mock_read_files.assert_called_once()
        call_args = self.mock_read_files.call_args[0]
        self.assertEqual(call_args[1], ["path/to/file1.java"])
        self.assertIn("mock file contents", result)

    def test_multiple_files_comma_separated(self):
        response = """Analysis complete.
        
        **Next Steps**
        [I need content of files: com/example/File1.java, com/example/File2.java, com/example/File3.java]
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        self.mock_read_files.assert_called_once()
        call_args = self.mock_read_files.call_args[0]
        expected_files = [
            "com/example/File1.java",
            "com/example/File2.java",
            "com/example/File3.java"
        ]
        self.assertEqual(call_args[1], expected_files)

    def test_file_request_with_spaces_and_newlines(self):
        response = """Looking at the code.
        
        **Next Steps**
        [I need content of files:
            com/example/File1.java,
            com/example/File2.java]
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        self.mock_read_files.assert_called_once()
        call_args = self.mock_read_files.call_args[0]
        expected_files = [
            "com/example/File1.java",
            "com/example/File2.java"
        ]
        self.assertEqual(call_args[1], expected_files)

    def test_file_request_with_failed_files(self):
        # Mock read_files to return some failed files
        self.mock_read_files.return_value = (
            "mock content",
            ["file1.java"],
            ["file2.java", "file3.java"]
        )
        
        response = """Analyzing code.
        
        **Next Steps**
        [I need content of files: file1.java, file2.java, file3.java]
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        # Check that failed files are mentioned in the result
        self.assertIn("could not be found or accessed: file2.java, file3.java", result)
        self.assertIn("mock content", result)

    def test_no_file_requests(self):
        response = """This is a response without any file requests.
        
        **Next Steps**
        Let's proceed with the analysis.
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        self.mock_read_files.assert_not_called()
        self.assertEqual(result, "")

    def test_alternative_file_request_format(self):
        response = """Checking the implementation.
        
        **Next Steps**
        [I need access files: path/to/file1.java]
        """
        
        result = extract_and_process_next_steps(response, self.mock_pf)
        
        self.mock_read_files.assert_called_once()
        call_args = self.mock_read_files.call_args[0]
        self.assertEqual(call_args[1], ["path/to/file1.java"])
        self.assertIn("mock file contents", result)

    def test_search_request_with_keywords(self):
        response = """Analysis in progress.
        
        **Next Steps**
        [I need to search for keywords: <keyword>#APPEND#</keyword>, <keyword>JobProcessorUtils</keyword>]
        """
        
        # Mock efficient_file_search to return some results
        with patch('llm_interaction.efficient_file_search') as mock_search:
            mock_search.side_effect = [
                ["file1.java"],  # results for #APPEND#
                ["file2.java", "file3.java"]  # results for JobProcessorUtils
            ]
            
            result = extract_and_process_next_steps(response, self.mock_pf)
            
            # Verify search was called for both keywords
            self.assertEqual(mock_search.call_count, 2)
            self.assertIn("#APPEND#", result)
            self.assertIn("JobProcessorUtils", result)
            self.assertIn("file1.java", result)
            self.assertIn("file2.java", result)

if __name__ == '__main__':
    unittest.main() 