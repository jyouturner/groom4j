import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from integration.git_utils import find_commit_hash


class TestGitUtils(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for our test git repo
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        # Initialize a git repo in the temporary directory
        self._run_git_command(["git", "init"])
        
        # Configure git user for commits
        self._run_git_command(["git", "config", "user.name", "Test User"])
        self._run_git_command(["git", "config", "user.email", "test@example.com"])
        
        # Create a test file and commit it
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Test content")
        self._run_git_command(["git", "add", "test.txt"])
        self._run_git_command(["git", "commit", "-m", "Initial commit"])

    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    def _run_git_command(self, command):
        """Helper method to run git commands in the test repo"""
        subprocess.run(
            command, 
            cwd=self.repo_path, 
            check=True, 
            capture_output=True
        )

    def test_find_commit_hash(self):
        # Get the actual branch name and commit hash using git commands
        branch_process = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        expected_branch = branch_process.stdout.strip()
        
        hash_process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        expected_hash = hash_process.stdout.strip()
        
        # Call our function and verify results
        branch, commit_hash = find_commit_hash(self.repo_path)
        
        self.assertEqual(branch, expected_branch)
        self.assertEqual(commit_hash, expected_hash)
    
    def test_non_git_directory(self):
        # Create a new empty directory (not a git repo)
        with tempfile.TemporaryDirectory() as non_git_dir:
            # Verify that our function raises an error
            with self.assertRaises(RuntimeError) as context:
                find_commit_hash(non_git_dir)
            
            self.assertIn("not a git repository", str(context.exception))


if __name__ == "__main__":
    unittest.main()