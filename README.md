# Grooming Java Development Tasks with LLM

## Project Goal

This project aims to provide Java development assistance by focusing on task "grooming" rather than direct code generation. Our approach is designed to:

1. Support entry-level developers by providing a clear path forward before coding begins.
2. Integrate seamlessly with existing development processes, including Jira workflows.
3. Effectively handle large codebases and inter-project dependencies.
4. Offer language-specific assistance tailored to Java projects.

## Why Grooming Matters

LLM-based development tools often fall short in real-world scenarios:

1. They rely heavily on conversational interactions, which can be inefficient for complex projects.
2. They struggle with understanding large codebases and project structures.
3. They lack the specificity needed for language-specific optimizations.

Our grooming-focused approach addresses these limitations by providing structured, context-aware assistance.

## Inspiration

This project draws inspiration from the research paper ["A Human-Inspired Reading Agent with Gist Memory of Very Long Contexts"](https://arxiv.org/abs/2402.09727). We apply a similar gisting approach to Java development tasks, enabling efficient navigation and understanding of complex projects.

The research paper discusses "ReadAgent," a system inspired by how humans read and understand long documents. Unlike current computer models that struggle with very long texts, ReadAgent mimics human reading by breaking texts into manageable parts (episodes), summarizing them into "gist memories" (key ideas), and referring back to the original text for details when necessary. This approach helps ReadAgent understand and remember the main points from long documents better than traditional methods, allowing it to perform better on tasks that involve reading comprehension of lengthy texts.

below image from [https://read-agent.github.io/](https://read-agent.github.io/) demontrates the intuitive approach.

<img src="docs/read-agent.jpg" width="800" alt="read agent">

## How It Works

Similar to how human being appoach to any maintenance of legacy code, we ask LLM to do a one time "gisting"

1. **Gist Java programs**

We send the Java files to LLM one by one with prompt for summaries

<img src="docs/gist_files.png" width="600" alt="Gist the Files">

The results are stored in a local file "code_files.txt", this is our "index".

We can build our code files graph now.

<img src="docs/package_file_graph.png" width="800" alt="Package and Files graph">

2. **Gist Java packages**

We do a travers of the graph recusivingly from bottom up. For each package, we combine the summaries of sub-packages and files and send to LLM to summarize it.

<img src="docs/gist_packages.png" width="600" alt="Package and Files graph">

The results are saved in a local file "package_notes.txt" file.

3. **Grooming**

Once we have the "indexing" or "gisting" done. We can start to groom a development task, by ask LLM to provide steps to accomplish the task.

In the first prompt to LLM, we specify its role, the task to work on, and the brief information of the project (for example, the top-down tree view). We also instruct LLM to ask more information about files and packages whenver necessary. In the following conversations, we will provide the summary or notes of the files (including source code) or packages, this conversation will continue until the LLM does not need more information (or reach to the maximum round of conversations)

<img src="docs/ask.png" width="800" alt="Ask LLM">

## Getting Started

To set up and start using the Gist-Based Development Assistant:

```sh
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Set LLM and API Key

You can choose to use OpenAI, Gemini or Anthropic LLMs

```sh
cp .env.example .env
```

The .env should looks like below if OpenAI is used

```
USE_LLM=openai
OPENAI_API_KEY='sk-...'
```

## Tracing (Optional)

If you want to leverage any tracing options, for example, the Opensource Langtrace (<https://github.com/Scale3-Labs/langtrace>)

You can self host the langtrace stack at local, including the web app, the Postgres, etc. Refer to <https://docs.langtrace.ai/hosting/overview>

```sh
git clone https://github.com/Scale3-Labs/langtrace.git
docker compose up -d
```

Visit <http://localhost:3000>, Make sure to enable Java script on the browser.

## Java Project Source

You can use "project_root" to specify the Java repo location. For testing purpose, there is a sample Java project "travel-service-dev" included in the "data" folder. It is an open source project available at Github [https://github.com/ilkeratik/travel-service](https://github.com/ilkeratik/travel-service).

<img src="docs/travel_service_project_structure.png" width="500" alt="Travel Service Java Project Structure">

## Try the Example Java Project

The "gist" files are already created in the "data/travel-service-dev" project, under ".gist" folder. You can test the grooming with below command

```sh
python3 grooming_task.py --project_root=./data/travel-service-dev --task="add a new field 'mayor' to city, for the name of the mayor of the city"

python3 grooming_task.py --project_root=./data/travel-service-dev --task="add a new feature to search city by name"

python3 grooming_task.py --project_root=./data/travel-service-dev --task="refactor the Rest API to GraphQL"

```

## Try Your Project

### **Step One to Gist code files**

```sh
python3 gist_files.py --project_root=[path to the Java project]
```

It will take a while before all the Java files are gisted. You will see a txt file "code_files.txt" generated afterwards, under the ".gist" folder within the Java project.

### **Step Two to Gist packages**

```sh
python3 gist_packages.py --project_root=[path to the Java project]
```

After the process is done, you will see a file "package_notes.txt" created in the ".gist" folder.

## Groom Coding Task

```sh
python3 grooming_task.py --project_root=[path to the Java project]--task="..."
```

## Groom A JIRA issue

In reality, developers often work on development stories from Jira. In this case, you can set up the necessary credentials and we can read the Jira story directly.

Make sure to set the JIRA properties in the .env file first.

```sh
JIRA_SERVER="https://[domain].atlassian.net"
JIRA_USERNAME="your email address"
JIRA_API_TOKEN="your API token"
```

```sh
python3 grooming_task.py --project_root=[path to the project] --jira=[issue key]

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

## Roadmaps

1. **Integration with Internal Knowledge Bases**

Large organizations often have extensive internal documentation, wikis, and presentations that explain various aspects of their systems. For example, setup a RAG (Retrieval-Augmented Generation) based system, potentially using GraphRAG to index those documents and provide query interface. Then integrate this tool with such RAG system for Q/A.

2. **Leveraging Approved Pull Requests (PRs)**

Pull requests are a gold mine of information on how to implement new features or fix issues. We can apply the similar strategy to index those PRs and code changes.

3. **Leverage Integration Testing**

Integration tests are a valuable resource for understanding how a project interacts with its dependencies and how data flows between systems. In today's microservices-oriented world, these tests often encapsulate critical knowledge about system interactions.