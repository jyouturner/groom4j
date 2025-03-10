import os
import sys
import argparse
import logging
from gist.projectfiles import ProjectFiles
from researcher.main import answer_question
from researcher.functions import save_response_to_markdown

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grooming development task")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    parser.add_argument("--task", type=str, default="", help="Development task, for example 'Add a health check endpoint to the web service'")
    parser.add_argument("--jira", type=str, default="", help="URL of the Jira ticket")
    parser.add_argument("--max-rounds", type=int, default=8, help="Maximum rounds of conversation with LLM before stopping the conversation")
    args = parser.parse_args()

    # Convert to absolute path if it's a relative path
    root_path = os.path.abspath(args.project_root)
    if not os.path.exists(root_path):
        logger.error(f"Error: {root_path} does not exist")
        sys.exit(1)

    # Initialize ProjectFiles
    pf = ProjectFiles(repo_root_path=root_path)
    pf.from_gist_files()

    # Get task description from either direct input or JIRA
    task = args.task
    if not task and args.jira:
        from integration import MyJira
        myJira = MyJira(
            host=os.environ.get("JIRA_SERVER"),
            user=os.environ.get("JIRA_USERNAME"),
            api_token=os.environ.get("JIRA_API_TOKEN")
        )
        issue = myJira.find_issue(args.jira)
        task = issue.fields.description
    
    if not task:
        logger.error("Please provide either task or jira")
        sys.exit(1)

    logger.info(f"Processing task: {task}")
    
    # Use researcher's answer_question function
    response, reviewer = answer_question(
        pf=pf,
        question=task,
        max_rounds=args.max_rounds,
        thoroughness=8  # Higher thoroughness for development tasks
    )

    # Save the response
    result_file = save_response_to_markdown(task, response, path=root_path+"/.gist/tell_me_about/")
    logger.info(f"Response saved to {result_file}")
