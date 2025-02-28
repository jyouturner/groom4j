# Conversation 1.1

User:

For the "Code Analysis" step, for the POC, I may just use LLM to summarize the programs, even including each functionalities and dependencies. For the "Pull Request Analysis" step, I can also use LLM to summarize the "task" and "changes". I figure I can have the data in any format I want.

The part I am not clear is the knowledge graph component. Given the results from the code analysis and PR analysis, how to build such graph? And when given a JIRA story (the ask or task), how to leverage the graph?

AI:

You're on the right track with using LLMs for code and pull request summarization in your POC. This approach will give you structured data to work with, which is excellent for building your knowledge graph. Let's dive into how you can construct and utilize the knowledge graph based on these summaries.

## Building the Knowledge Graph

Given the results from your code analysis and PR analysis, you can build a knowledge graph as follows:

1. Define Node Types:
    - Code Entities (e.g., Classes, Methods, Packages)
    - Pull Requests
    - JIRA Stories
    - Developers (authors of PRs or code changes)
2. Define Relationship Types:
    - "DEPENDS_ON" (between code entities)
    - "IMPLEMENTS" (between methods and interfaces)
    - "MODIFIES" (between PRs and code entities)
    - "RELATES_TO" (between JIRA stories and code entities or PRs)
    - "AUTHORED_BY" (between code entities or PRs and developers)
3. Populate the Graph:
    - For each code entity in your summaries, create a node with properties like name, type, and summary.
    - For each dependency identified, create a "DEPENDS_ON" relationship between the relevant nodes.
    - For each PR, create a node with properties like ID, summary, and changes.
    - Create "MODIFIES" relationships between PR nodes and the code entities they change.
    - If you have historical JIRA data, create nodes for stories and link them to relevant code entities or PRs.

Here's a simple example of how you might create this graph using Python and the Neo4j graph database:

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def add_code_entity(tx, name, entity_type, summary):
    tx.run("CREATE (e:CodeEntity {name: $name, type: $type, summary: $summary})",
           name=name, type=entity_type, summary=summary)

def add_dependency(tx, entity1, entity2):
    tx.run("MATCH (e1:CodeEntity {name: $entity1}), (e2:CodeEntity {name: $entity2}) "
           "CREATE (e1)-[:DEPENDS_ON]->(e2)",
           entity1=entity1, entity2=entity2)

def add_pr(tx, pr_id, summary, changes):
    tx.run("CREATE (pr:PullRequest {id: $id, summary: $summary, changes: $changes})",
           id=pr_id, summary=summary, changes=changes)

def link_pr_to_entity(tx, pr_id, entity_name):
    tx.run("MATCH (pr:PullRequest {id: $pr_id}), (e:CodeEntity {name: $entity_name}) "
           "CREATE (pr)-[:MODIFIES]->(e)",
           pr_id=pr_id, entity_name=entity_name)

# Example usage
with driver.session() as session:
    session.write_transaction(add_code_entity, "UserService", "Class", "Manages user operations")
    session.write_transaction(add_code_entity, "AuthService", "Class", "Handles authentication")
    session.write_transaction(add_dependency, "UserService", "AuthService")
    session.write_transaction(add_pr, "PR-123", "Add user registration", "Modified UserService")
    session.write_transaction(link_pr_to_entity, "PR-123", "UserService")

driver.close()
```


## Leveraging the Graph for JIRA Stories

When given a new JIRA story, you can leverage the knowledge graph to provide context and insights. Here's how:

1. Analyze the JIRA Story:
Use your LLM to extract key information from the story description, such as affected components or related functionality.
2. Query the Knowledge Graph:
Based on the extracted information, query the graph to find relevant nodes and relationships. For example:

```python
def find_related_entities(tx, keyword):
    result = tx.run("MATCH (e:CodeEntity) "
                    "WHERE e.summary CONTAINS $keyword "
                    "RETURN e.name, e.type, e.summary",
                    keyword=keyword)
    return list(result)

def find_recent_prs(tx, entity_name):
    result = tx.run("MATCH (pr:PullRequest)-[:MODIFIES]->(e:CodeEntity {name: $name}) "
                    "RETURN pr.id, pr.summary ORDER BY pr.id DESC LIMIT 5",
                    name=entity_name)
    return list(result)
```

3. Generate Insights:
Use the query results to provide valuable information for grooming:
    - Identify potentially affected components
    - List recent changes to related code (from PRs)
    - Highlight dependencies that might be impacted
    - Suggest developers who have recently worked on related code
4. Update the Graph:
As the story progresses, update the graph by creating a new JIRA story node and linking it to relevant entities:

```python
def add_jira_story(tx, story_id, summary):
    tx.run("CREATE (s:JiraStory {id: $id, summary: $summary})",
           id=story_id, summary=summary)

def link_story_to_entity(tx, story_id, entity_name):
    tx.run("MATCH (s:JiraStory {id: $story_id}), (e:CodeEntity {name: $entity_name}) "
           "CREATE (s)-[:RELATES_TO]->(e)",
           story_id=story_id, entity_name=entity_name)
```

5. Continuous Learning:
As new PRs are created and merged, update the graph to reflect the latest changes and relationships. This ensures that future queries will have access to the most up-to-date information.

By following this approach, your AI assistant can provide contextually rich information during the grooming process, helping teams better understand the potential impact and complexity of new stories based on historical data and code relationships.

Remember, the effectiveness of this system will improve over time as more data is added to the graph and as you refine your querying and insight generation processes based on user feedback and observed patterns in your specific project context.

