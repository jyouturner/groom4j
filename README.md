# Groom4J: LLM-Powered Task Planning for Java Projects


## 🎯 Bridging the Gap in Enterprise Java Development

Groom4J is designed to address a critical challenge in enterprise Java development: helping new or entry-level developers navigate and understand complex, established codebases. Unlike general-purpose coding assistants, Groom4J is tailored specifically for Java projects in enterprise environments, where the primary hurdles are often not in writing code, but in:

- **Understanding the big picture**: Grasping how different components of a large Java application interact.
- **Connecting the dots**: Identifying relationships between various packages, classes, and services.
- **Finding the starting point**: Determining where to begin when tackling a new task or bug fix.
- **Navigating internal complexity**: Making sense of company-specific architectures, patterns, and legacy code.

## What Sets Groom4J Apart:

1. **Java-Specific Intelligence**: Leverages deep understanding of Java language structures, common enterprise patterns, and best practices.
2. **Focus On Development Process**: Tailored for the unique challenges of large-scale, complex Java projects common in enterprise development process where coding is just one step in the middle.
3. **Context-Aware Assistance**: Provides insights that consider the entire project structure, not just isolated code snippets.
4. **Practical Task Planning**: Helps break down high-level tasks into actionable steps, considering the specific project context.
5. **Onboarding Accelerator**: Dramatically reduces the time it takes for new team members to become productive on large Java projects.

By focusing on these aspects, Groom4J fills a crucial gap between generic coding tools and the specific needs of Java development teams in enterprise environments. It's not just about writing code—it's about understanding, navigating, and effectively contributing to complex Java ecosystems.

## Inspiration

More about this project can be found at [what inspired this project](docs/inspiration.md)


## Getting Started

This project uses Python 3.11+ and Poetry to manage dependencies. You can run it directly on your system or use Docker for easier setup, especially if you're not familiar with Python environments.


## Set LLM and API Key

You can choose to use OpenAI, Gemini or Anthropic LLMs

```sh
cp application_example.yml application.yml
```

Depends on the LLM provider, you need to set the corresponding API key in the application.yml file.

```yaml
llm:
  use: anthropic
  
anthropic:
  api_key: ...
  model: claude-3-5-sonnet-20240620
```


### Running with Poetry (for Python developers)

If you have Python and Poetry installed:

1. Install dependencies:

   ```sh
   poetry install
   ```
2. Run Tool

```sh
poetry run python gist_files.py path/to/the/Java/Project/Repo
poetry run python gist_packages.py path/to/the/Java/Project/Repo
poetry run python grooming_task.py path/to/the/Java/Project/Repo --task="Your task description"
```

### Running with Docker (recommended for Java developers)

If you prefer using Docker or are not familiar with Python environments:

Install Docker on your system if you haven't already.

Use the provided run-read-agent.sh script to run the tool:

```sh
# To gist files
./run-read-agent.sh gist-files /path/to/your/java/project

# To gist packages
./run-read-agent.sh gist-packages /path/to/your/java/project

# To groom a task
./run-read-agent.sh groom-task --task="Your task description" /path/to/your/java/project
```

The script will automatically build the Docker image if needed and run the tool inside a container using Poetry. The Java project directory is mounted into the container, allowing the tool to access and analyze the project files.

Note: Make sure you have read access to the Java project directory you're trying to analyze.

## About Tracing (Optional)

This project supports opensource tracing tool langfuse (https://github.com/langfuse/langfuse)

```sh
git clone https://github.com/langfuse/langfuse
docker compose up -d
```

Visit <http://localhost:3000> to sign up, create a project, and create the API key. Then update the applicaiton.yml file with the API key.

```yaml
langfuse:
  secret_key: ...
  public_key: ...
  host: http://localhost:3000
```

## Example Java Project

For testing purpose, there is a sample Java project "travel-service-dev" included in the "data" folder. It is an open source project available at Github [https://github.com/ilkeratik/travel-service](https://github.com/ilkeratik/travel-service).

<img src="docs/travel_service_project_structure.png" width="500" alt="Travel Service Java Project Structure">

## Try the Example Java Project

The "gist" files are already created in the "data/travel-service-dev" project, under ".gist" folder. You can test the grooming with below command

```sh
poetry run python grooming_task.py ./data/travel-service-dev --task="add a new field 'mayor' to city, for the name of the mayor of the city"

poetry run python grooming_task.py ./data/travel-service-dev --task="add a new feature to search city by name"

poetry run python grooming_task.py ./data/travel-service-dev --task="refactor the Rest API to GraphQL"

```

or if you have a specific question to ask

```sh
poetry run python tell_me_about.py ./data/travel-service-dev/ --question="how data flow from database to the API"
```

or just use a dedicated script to find info in the API projects, which will generate a markdown file (api_note.md) under ".gist" folder

```sh
poetry run python summarize_api.py ./data/travel-service-dev
```

## Use on Your Project

### **Step One to Gist code files**

```sh
poetry run python gist_files.py path/to/the/Java/Project/Repo
```

It will take a while before all the Java files are gisted. You will see a txt file "code_files.txt" generated afterwards, under the ".gist" folder within the Java project.

### **Step Two to Gist packages**

```sh
poetry run python gist_packages.py path/to/the/Java/Project/Repo
```

After the process is done, you will see a file "package_notes.txt" created in the ".gist" folder.

### **Optional to Gist API**

If your project is a API project, there is a dedicated script to create a markdown file to describe the endpoints of the API.

```sh
poetry run python gist_api.py path/to/the/Java/Project/Repo
```

After the process is done, you will see a mardown file "api_notes.md" created in the ".gist" folder.


## Q&A

If you have a specific question to ask about the codebase, you can use below command to inspect the codebase

```sh
poetry run python grooming_task.py path/to/the/Java/Project/Repo --question="..."
```

More info can be found in [tell_me_about](docs/tell_me_about.md)

## Groom Coding Task

Development tasks and stories are often bigger than one single Q/A, you can use below command for the "grooming" purpose.

```sh
poetry run python grooming_task.py path/to/the/Java/Project/Repo --task="..."
```

## Groom A JIRA issue

In reality, developers often work on development stories from Jira. In this case, you can set up the necessary credentials and we can read the Jira story directly.

Make sure to set the JIRA properties in the .env file first.

```yaml
jira:
  server: https://[host].atlassian.net
  username: email@domain.com
  api_token: ...
```

```sh
poetry run python grooming_task.py path/to/the/Java/Project/Repo --jira=[issue key]
```

## Examples

<img src="docs/gist_files_tracing.jpg" width="600" alt="tracing image of gisting files">

<img src="docs/gist_package_tracing.jpg" width="600" alt="tracing image of gisting package">

<img src="docs/ask_tracing.jpg" width="600" alt="tracing image of asking">

## Common Questions

### Is this similar to the "planning" phase in agentic coding assistants?

Yes, this project essentially covers the "planning" phase found in AI coding assistants like Open-Devin. We use the term "grooming" to align with common development team workflows, potentially integrating with Sprint planning or JIRA. Our focus is on supporting entry-level or junior engineers often assigned maintenance tasks in enterprise environments, where challenges frequently relate to domain knowledge, edge cases, integration testing, and dependency management.

### How does this compare to RAG or GraphRAG?

While similar to Retrieval-Augmented Generation (RAG) in that it indexes documents first, our approach is specifically tailored for Java projects. It leverages the intrinsic structure of Java codebases, similar to GraphRAG's concept of connecting information nodes. We create a graph of Java programs, packages, and projects to provide context-aware assistance.

### Doesn't this reinvent existing Java code indexing tools?

While Java IDEs have long had powerful code indexing capabilities (e.g., Eclipse's JDT Core Index), our approach leverages the natural language understanding of LLMs. This allows for more flexible and intuitive interactions with the codebase, potentially reducing the need for complex integration with legacy indexers.

### Why not use function calling for file and package requests?

Function calling is on our roadmap for future improvements. The current approach using prompts and parsing works well across various LLMs (except for some limitations with Gemini). It provides a simple, consistent interface for requesting file and package information:

```
[I need access files: <file>file1 name</file>,<file>file2 name</file>]
[I need info about packages: <package>package name</package>]
[I need to search <keyword>keyword</keyword> in the project]
```

### Will this be necessary when LLMs can process entire repositories?

While LLMs are evolving rapidly, handling private, enterprise-scale codebases with full context remains challenging. Until we can effectively fine-tune LLMs on internal repositories (considering security and privacy concerns), systems like this serve as crucial "assistants to LLMs." They provide structured, context-aware information to help LLMs navigate and understand complex project structures more effectively.

### How does this tool benefit development teams?

1. **Context-Aware Assistance**: By gisting files and packages, it provides LLMs with a hierarchical understanding of the project structure.
2. **Efficient Onboarding**: Helps new team members quickly grasp project architecture and dependencies.
3. **Consistent Approach**: Encourages a standardized method for task planning and code navigation across the team.
4. **Integration Potential**: Designed to work alongside existing tools and processes, enhancing rather than replacing current workflows.

## To Do

### **Handle Code Changes**

Instead of re-index (gist) the whole project, we need to find the diff betweeen the commits and only update the gist files of the changes since the last success indexing.

### **Multi-Agent**


### **Implement a "critical thinking" phase**

Before proposing solutions, prompt the LLM to critically evaluate its own assumptions and initial ideas
Ask it to consider alternative explanations for the observed behavior

### **Implement a review and refinement stage**

After the initial analysis, prompt the LLM to review its own work
Ask it to identify potential oversights or areas that need more investigation

### **Integration with Internal Knowledge Bases**

Large organizations often have extensive internal documentation, wikis, and presentations that explain various aspects of their systems. For example, setup a RAG (Retrieval-Augmented Generation) based system, potentially using GraphRAG to index those documents and provide query interface. Then integrate this tool with such RAG system for Q/A.

### **Leveraging Approved Pull Requests (PRs)**

Pull requests are a gold mine of information on how to implement new features or fix issues. We can apply the similar strategy to index those PRs and code changes.

### **Leverage Integration Testing**

Integration tests are a valuable resource for understanding how a project interacts with its dependencies and how data flows between systems. In today's microservices-oriented world, these tests often encapsulate critical knowledge about system interactions.

### **Add Cost Estimate**

Estimate the cost before and after gisting files and grooming tasks.