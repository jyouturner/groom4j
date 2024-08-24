import unittest
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_utils import load_config_to_env

class TestConfigUtils(unittest.TestCase):

    def setUp(self):
        # Clear environment variables before each test
        for key in list(os.environ.keys()):
            if not key.startswith('PYTEST_'):
                del os.environ[key]

    def test_load_config_to_env_success(self):
        mock_yaml_content = """
        test:
          key1: value1
          nested:
            key2: value2
        another_key: value3
        """
        mock_file = mock_open(read_data=mock_yaml_content)
        
        with patch('builtins.open', mock_file):
            with patch.object(Path, 'exists', return_value=True):
                load_config_to_env()

        self.assertEqual(os.environ.get('TEST_KEY1'), 'value1')
        self.assertEqual(os.environ.get('TEST_NESTED_KEY2'), 'value2')
        self.assertEqual(os.environ.get('ANOTHER_KEY'), 'value3')

    def test_load_config_to_env_file_not_found(self):
        with patch.object(Path, 'exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                load_config_to_env()

    def test_load_config_to_env_invalid_yaml(self):
        mock_yaml_content = "invalid: yaml: content:"
        mock_file = mock_open(read_data=mock_yaml_content)
        
        with patch('builtins.open', mock_file):
            with patch.object(Path, 'exists', return_value=True):
                with self.assertRaises(Exception):  # You might want to catch a more specific exception if possible
                    load_config_to_env()

if __name__ == '__main__':
    unittest.main()