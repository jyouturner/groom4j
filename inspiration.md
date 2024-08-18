# More About This Project

## The Vision Behind JavaGroom

As an engineering manager in a large corporation, I've observed a recurring challenge: new engineers, especially entry-level developers and recent graduates, often struggle when first encountering large, legacy codebases. Contrary to popular belief, the act of writing code itself isn't their biggest hurdle. Instead, the real challenges lie in:

1. **Connecting the Dots**: Understanding how different parts of the system interact and depend on each other.
2. **Navigating Complexity**: Making sense of intricate internal structures and various dependencies.
3. **Tracing Data Flow**: Following how data moves through the system, from database to API and beyond.
4. **Grasping the Big Picture**: Seeing beyond individual classes or functions to understand the overall system architecture.

## Why Current Coding Assistants Fall Short

While many coding assistants excel at generating code snippets or explaining isolated concepts, they often fall short in providing the holistic understanding crucial for working on enterprise-scale projects. They may help write a function, but they struggle to explain where that function fits in the grand scheme of a complex application.

## The JavaGroom Approach

JavaGroom is born from the conviction that truly empowering new developers means focusing on understanding and planning, rather than just coding. Our approach is based on the belief that:

1. **Comprehension Precedes Coding**: Once developers understand the system, writing code becomes significantly easier and more effective.
2. **Context is King**: Providing context-aware assistance that considers the entire project ecosystem is more valuable than isolated code generation.
3. **Planning is Paramount**: Breaking down tasks with a deep understanding of the project's structure leads to more efficient and accurate development.

## Our Goal

The primary goal of JavaGroom is to create a tool that:

1. Accelerates the onboarding process for new developers in large Java projects.
2. Enhances overall project understanding for all team members.
3. Improves the quality of code and architectural decisions by providing better context.
4. Reduces the time spent on task planning and increases the accuracy of estimations.
5. Bridges the gap between high-level project goals and low-level implementation details.

By focusing on these aspects, we aim to not just assist with coding, but to elevate the overall capabilities of development teams, particularly in navigating and maintaining large, complex Java applications in enterprise environments.


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