#
# functions to interact with git
#

def find_commit_hash(project_root) -> tuple[str, str]:
    """
    Find the current branch name and commit hash.
    
    Args:
        project_root: Path to the git repository root
        
    Returns:
        tuple: (branch_name, commit_hash)
        
    Raises:
        RuntimeError: If git is not available or if the directory is not a git repository
    """
    import subprocess
    import os
    import shutil
    
    # Check if git is available
    if not shutil.which("git"):
        raise RuntimeError("Git is not available in the system PATH")
    
    # Change to the project root directory
    original_dir = os.getcwd()
    os.chdir(project_root)
    
    try:
        # Check if this is a git repository
        check_cmd = ["git", "rev-parse", "--is-inside-work-tree"]
        check_process = subprocess.run(check_cmd, capture_output=True, text=True)
        if check_process.returncode != 0:
            raise RuntimeError(f"Directory {project_root} is not a git repository")
        
        # Get current branch name
        branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        branch_process = subprocess.run(branch_cmd, capture_output=True, text=True)
        if branch_process.returncode != 0:
            raise RuntimeError(f"Failed to get branch name: {branch_process.stderr.strip()}")
        branch_name = branch_process.stdout.strip()
        
        # Get current commit hash
        hash_cmd = ["git", "rev-parse", "HEAD"]
        hash_process = subprocess.run(hash_cmd, capture_output=True, text=True)
        if hash_process.returncode != 0:
            raise RuntimeError(f"Failed to get commit hash: {hash_process.stderr.strip()}")
        commit_hash = hash_process.stdout.strip()
        
        return branch_name, commit_hash
    
    finally:
        # Return to original directory
        os.chdir(original_dir)