# Conversation 1

User:

I am working on a AI assistant that focuses on grooming jira stories of enterprise legacy java projects. Although i understand there are already indexing techniques existing like ATS, i am wondering two different approaches together:

1, use LLM to analyze java programs and summarize the info, and dependencies
2, have a knowledge graph to record the relationships.

Specifically, not only apply above to the code files, but also leverage the previous pull requests which can give us "ask" and "answer" typescript of data.

I figure, with the knowledge graph argument, to improve the AI grooming assistant RAG

AI:

Modern AI approaches can significantly improve the efficiency and effectiveness of grooming Jira stories for enterprise legacy Java projects. By combining Large Language Models (LLMs) for code analysis with knowledge graphs for relationship mapping, and leveraging historical pull request data, we can create a sophisticated Retrieval Augmented Generation (RAG) system that provides contextually rich assistance for story refinement. This report explores how these technologies can work together to transform the grooming process for legacy systems.

## Understanding the Challenges of Legacy Java Project Grooming

Enterprise legacy Java projects present unique challenges when it comes to backlog grooming. These systems often contain complex, interconnected components developed over years or decades, with varying documentation quality and institutional knowledge scattered across teams. Backlog grooming for such systems requires a deep understanding of both the codebase and the business domain to effectively prioritize and refine work items.

Backlog grooming in Jira involves managing and refining the list of work items, tasks, and user stories to keep the project on track and the team focused on priorities[^4]. However, when dealing with legacy systems, the task becomes significantly more complex due to the obscurity of low-level logic that hinders understanding, modeling for refactoring efforts, and onboarding new developers[^5]. This is precisely where AI-driven approaches can provide substantial value.

## Leveraging LLMs for Legacy Java Code Analysis

The first approach you've identified—using LLMs to analyze Java programs and summarize information and dependencies—has significant potential for enhancing the grooming process. LLMs can be employed to generate comprehensive code summaries and identify dependencies that might otherwise require extensive manual review.

Recent advancements in code summarization techniques have made this approach increasingly viable. Modern LLM models utilizing transformer-based architectures can effectively summarize code by understanding both the programming language syntax and the underlying logic it implements[^8]. These models can generate natural language descriptions of code snippets, which is particularly valuable for legacy systems where documentation may be sparse or outdated.

However, it's important to note that there are limitations to LLM-based direct code translation, especially for critical legacy systems where errors cannot be tolerated[^5]. Documentation generation or code summarization emerges as a more reliable strategy in these cases. Even when LLM-driven code translation might not be trustworthy, automatically generated documentation can accelerate code understanding to facilitate translation, refactoring, and maintenance if it can be generated consistently and accurately[^5].

For analyzing Java dependencies specifically, LLMs can be trained to identify relationships between components, libraries, and modules. This is particularly valuable in legacy systems where dependencies may not be explicitly documented or may have evolved over time. By identifying these relationships, the LLM can provide insights into how changes to one component might impact others, which is crucial information during backlog grooming.

## Building Knowledge Graphs for Relationship Mapping

The second approach you've identified—using knowledge graphs to record relationships—complements the LLM-based code analysis beautifully. Knowledge graphs excel at representing complex relationships between entities, making them ideal for mapping dependencies in large codebases.

Knowledge graphs store data as a network of nodes and the relationships between them, allowing for efficient navigation from one piece of information to another[^6]. This connected data structure is particularly well-suited for handling complex, multi-part questions that involve connecting the dots between associated pieces of information—precisely the type of queries that arise during backlog grooming sessions.

For legacy Java projects, a knowledge graph could represent entities such as:

Classes and interfaces with their inheritance relationships
Method calls and dependencies
Package structures and their organizational hierarchy
Database tables and their relationships to code entities
API endpoints and their implementations

The process of building such a knowledge graph typically involves parsing the codebase to extract structural information. Tools that combine LLMs with knowledge graphs derived from abstract syntax trees (ASTs) of codebases have shown positive results in drawing out low-level requirements and building high-level explanations of systems[^15]. This approach can be particularly valuable for legacy systems where the original design documentation may be lacking.

## Leveraging Pull Request History as Training Data

Your insight about leveraging previous pull requests as sources of "ask" and "answer" typescripts is particularly valuable. Pull requests contain rich information about code changes, including:

The problem being solved (in the PR description)
The solution approach (in the code changes)
Review comments highlighting potential issues or alternative approaches
Final resolution and merged changes

This historical data serves as an excellent training corpus for teaching an LLM about project-specific patterns, coding standards, and common issues. By analyzing this history, the LLM can better understand the context of the codebase and provide more relevant suggestions during the grooming process.

When creating pull requests, descriptive titles and descriptions that clearly explain the purpose and provide relevant context are essential[^3]. This metadata, combined with the actual code changes, provides valuable insights into the evolution of the codebase and the rationale behind design decisions.

## Integrating Knowledge Graphs with RAG for Enhanced Grooming

The combination of knowledge graphs and LLMs through a Retrieval Augmented Generation (RAG) approach—sometimes called GraphRAG—has shown promising results for handling complex, multi-part questions[^6]. Traditional RAG applications excel at answering simple questions by integrating data from external sources into LLMs but struggle with questions that require connecting information from multiple sources. Knowledge graphs overcome this limitation by explicitly modeling relationships between entities.

RAG stands for Retrieval Augmented Generation, and it's used to retrieve precise information about specific subjects to improve requests for information[^14]. By controlling the content your AI assistant pulls information from, you can ensure precise responses to queries during grooming sessions.

In the context of a Jira grooming assistant, GraphRAG offers several advantages:

Contextual understanding: By traversing the knowledge graph, the system can understand relationships between components and provide more comprehensive insights.
Multi-hop reasoning: The system can answer questions that require connecting multiple pieces of information, such as "What would be the impact of changing this API endpoint on the front-end components?"
Precise retrieval: The system can retrieve exactly the relevant information needed to address a specific grooming question, rather than returning entire documents.

The information extraction pipeline, which extracts structured information from unstructured text in the form of entities and relationships, can be combined with knowledge graphs to process documents individually[^6]. When the knowledge graph is constructed or enriched, information from different records gets connected, making it easy to answer questions that span multiple documents.

## Implementation Considerations and Best Practices

### Technical Architecture

To implement the proposed solution, you might consider the following architecture:

1. Code Analysis Component:
    - Use abstract syntax tree (AST) parsers to extract structural information from Java code
    - Apply LLMs like Llama 3.1 8B Instruct for code summarization[^1]
    - Implement parameter training using techniques like LoRA to fine-tune the model for your specific codebase[^1]
2. Knowledge Graph Component:
    - Store code entities and relationships in a graph database like Neo4j[^16]
    - Implement graph visualization tools using libraries like Pyvis to provide intuitive interfaces for exploring relationships[^3]
    - Connect the knowledge graph to your existing data sources using appropriate connectors[^16]
3. Pull Request Analysis:
    - Implement GitHub API integrations to extract historical pull request data
    - Process PR descriptions, comments, and code changes to extract valuable context
    - Use this data to fine-tune your LLM models for project-specific understanding
4. RAG System:
    - Implement a retrieval system that can query both text embeddings and graph relationships
    - Develop prompt engineering techniques for effective knowledge graph traversal
    - Integrate with Jira's API to access and update story information

### Observability and Monitoring

Implementing observability into your LLM-based assistant is crucial for ensuring reliable performance. Tools like LlamaIndex for Java can help with collecting metrics and traces[^2]. This includes:

- Setting up Prometheus for metrics collection
- Configuring Jaeger for tracing
- Implementing LangSmith for debugging LLM applications[^2]

These observability tools help in identifying where things might go wrong in your LLM application, visualizing the flow of data, and actively debugging and refining your models[^2].

### Security Considerations

When implementing LLM packages in your application, be mindful of security considerations. Research has found that 95% of applications using dependencies of software component packages make calls to security-sensitive APIs[^9]. Additionally, LLMs are not yet reliable at malware detection, with studies showing accuracy rates of only 3.4% to 7.9%[^9]. Regular security audits and careful vetting of dependencies are essential.

## Integrating with Jira Backlog Grooming Workflows

The ultimate goal is to enhance the Jira backlog grooming process, which involves several key activities:

1. Reviewing items in the backlog to identify high-priority tasks
2. Adding detailed descriptions and acceptance criteria
3. Estimating effort required for each task
4. Breaking down large tasks into smaller, more manageable pieces
5. Removing obsolete or irrelevant items[^4]

Your AI assistant can support each of these activities by:

Analyzing code to provide context for user stories
Identifying dependencies that might affect prioritization
Suggesting acceptance criteria based on code behavior
Estimating complexity based on similar historical stories
Recommending task breakdowns based on code structure

By integrating with Jira's API, the assistant can retrieve story information, provide augmented insights during grooming sessions, and potentially update stories based on approved suggestions.

## Conclusion

Combining LLMs for Java code analysis with knowledge graphs for relationship mapping represents a powerful approach to enhancing Jira story grooming for legacy enterprise systems. By leveraging historical pull request data as a rich source of context and integrating these technologies through a sophisticated RAG system, you can create an AI assistant that provides valuable insights during the grooming process.

This approach addresses the unique challenges of legacy systems by making implicit knowledge explicit, identifying hidden dependencies, and providing contextually relevant information to stakeholders. While implementing such a system requires careful consideration of technical architecture, security, and integration aspects, the potential benefits in terms of improved grooming efficiency and quality make it a worthwhile investment.

As you move forward with implementation, consider starting with a focused proof-of-concept that targets a specific aspect of the grooming process, such as dependency identification or code summarization. This will allow you to demonstrate value quickly while refining your approach based on real-world feedback. With iterative improvement, your AI-assisted grooming system can become an invaluable tool for managing complex legacy Java projects.

<div style="text-align: center">⁂</div>

[^1]: https://stackoverflow.com/questions/78855296/text-summarization-with-llm-llama-3-1-8b-instruct

[^2]: https://www.restack.io/p/llm-observability-answer-java-code-cat-ai

[^3]: https://www.restack.io/p/knowledge-graph-maker-answer-github-cat-ai

[^4]: https://community.atlassian.com/t5/App-Central-articles/Backlog-Grooming-in-Jira/ba-p/2775153

[^5]: https://arxiv.org/pdf/2411.14971.pdf

[^6]: https://neo4j.com/blog/developer/knowledge-graphs-llms-multi-hop-question-answering/

[^7]: https://github.com/christianrice/rag-coding-assistant

[^8]: https://www.ibm.com/think/tutorials/code-summarization-with-granite

[^9]: https://www.linkedin.com/pulse/dependencies-llm-packages-expose-apps-vulnerabilities

[^10]: https://stackoverflow.com/questions/27736883/how-to-get-googles-knowledge-graph-people-also-search-for-content

[^11]: https://www.youtube.com/watch?v=nSq97py1mrc

[^12]: https://vaadin.com/blog/using-ai-to-summarize-documents-in-java

[^13]: https://www.hillwebcreations.com/knowledge-graph-question-answering/

[^14]: https://ebi.ai/blog/rag-retrieval-augmented-generation/

[^15]: https://martinfowler.com/articles/legacy-modernization-gen-ai.html

[^16]: https://stackoverflow.com/questions/60054451/how-to-build-question-answering-program-based-on-knowledge-graph-in-python

[^17]: https://aclanthology.org/2024.lrec-main.89.pdf

[^18]: https://kindgeek.com/blog/post/experiments-with-langchain4j-or-java-way-to-llm-powered-applications

[^19]: https://github.com/Knowledge-Graph-Hub/kg-microbe/pulls

[^20]: https://community.atlassian.com/t5/Jira-questions/RAG-in-JIRA-Cloud/qaq-p/2153856

[^21]: https://par.nsf.gov/servlets/purl/10539763

[^22]: https://arxiv.org/html/2405.20455v3

[^23]: https://github.com/ygaitonde/knowledge-graph-api/pulls

[^24]: https://www.ksolves.com/blog/artificial-intelligence/sprint-planning-assistant-optimizing-jira-releases-with-rag-and-genai

[^25]: https://dl.acm.org/doi/fullHtml/10.1145/3551349.3559555

[^26]: https://www.csoonline.com/article/646676/dependencies-in-llm-packages-open-apps-to-vulnerabilities-report.html

[^27]: https://discuss.logseq.com/t/collaboration-for-a-kb-over-github-with-pull-requests/17958

[^28]: https://www.reddit.com/r/ProductManagement/comments/14eam37/anyone_else_avoid_using_the_word_grooming_for/

[^29]: https://www.youtube.com/watch?v=UjqomCXnkfs

[^30]: https://www.codemetal.ai/research/combining-ai-with-formal-verification-for-efficient-migration-of-legacy-code

[^31]: https://www.reddit.com/r/LangChain/comments/1d8uj3o/rag_how_to_answer_give_me_all_question/

[^32]: https://dzone.com/articles/building-an-ai-powered-professor-rating-assistant

[^33]: https://www.innoq.com/en/blog/2024/11/llm-assisted-abbreviation-mining/

[^34]: https://github.com/heathersherry/Knowledge-Graph-Tutorials-and-Papers/blob/master/topics/Knowledge Graph Question Answering (KGQA).md

[^35]: https://zilliz.com/blog/how-inkeep-and-milvus-built-rag-driven-ai-assisstant-for-smarter-interaction

[^36]: https://arxiv.org/html/2411.14971v1

[^37]: https://github.com/BshoterJ/awesome-kgqa

[^38]: https://codingscape.com/blog/best-ai-tools-for-retrieval-augmented-generation-rag

[^39]: https://www.javaadvent.com/2024/12/java-migrations-argh-and-now-large-language-models.html

[^40]: https://www.datasciencecentral.com/question-answering-based-on-knowledge-graphs/

