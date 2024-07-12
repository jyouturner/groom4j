from jira import JIRA, JIRAError
import logging

class MyJira:

    def __init__(self, host, user, api_token):
        self.jira = self.verify_jira_access(host, user, api_token)

    def verify_jira_access(self, host, user, api_token):
        try:
            # Attempt to create a JIRA client
            jira = JIRA(server=host, basic_auth=(user, api_token))
            
            # Try to access the server info
            server_info = jira.server_info()
            
            logging.info(f"Successfully connected to Jira instance: {server_info['serverTitle']}")
            logging.info(f"Base URL: {server_info['baseUrl']}")
            logging.info(f"Version: {server_info['version']}")

            # Get all projects viewable by anonymous users.
            projects = jira.projects()
            
            logging.debug(f"Found {len(projects)} projects:")
            return jira
        
        except JIRAError as e:
            if e.status_code == 401:
                logging.error("Error: Authentication failed. Please check your username and API token.")
            elif e.status_code == 404:
                logging.error("Error: Jira instance not found. Please check the server URL.")
            else:
                logging.error(f"An error occurred while connecting to Jira: {str(e)}")
            raise

    def find_issue(self, key):
        issue = self.jira.issue(key)
        return issue