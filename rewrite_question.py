import argparse
import sys

system_prompt_rewrite_question = """
You are an AI assistant designed to help expand and refine questions about Java projects. 
"""

instructions_rewrite_question = """

You are asked to help expand and refine questions about Java projects. Your task is to take an initial question from a developer and rewrite it to be more comprehensive, specific, and aligned with the project's structure and common Java development concerns.

## Context
- The question is about a Java project that has been "gisted" (summarized) for quick reference.
- The expanded question will be used to query a knowledge base of Java file summaries and project structure.
- The goal is to be **as thorough as possible** to help developers plan for maintenance tasks more effectively.

## Instructions

1. Analyze the given question and consider the following aspects of Java development:
   - Project structure and architecture
   - Design patterns and best practices
   - Performance considerations
   - Scalability and maintainability
   - Testing and quality assurance
   - Integration with other systems or libraries
   - Security concerns
   - Code readability and documentation

2. Expand the question to cover relevant areas that the developer might not have initially considered but are crucial for a comprehensive understanding of the task.

3. Include specific Java-related terminologies and concepts that are relevant to the question.

4. Ensure the expanded question is clear, concise, and focused on actionable insights.

5. If the original question is vague, add specificity based on common Java development scenarios.

6. Structure the expanded question to encourage exploration of both high-level architecture and low-level implementation details.

7. Include prompts for identifying potential challenges or areas that might require special attention during the maintenance task.

## Output Format

Provide your response in the following format:

```
Original Question: [Insert the original question here]

<Expanded_Question>
[Your expanded and refined question goes here. It should be a paragraph or two, or a series of related questions that dive deeper into the subject matter.]

Key Areas to Explore:
- [Area 1]
- [Area 2]
- [Area 3]
...

Potential Challenges to Consider:
- [Challenge 1]
- [Challenge 2]
- [Challenge 3]
...
</Expanded_Question>
```

## Example

Original Question: "How does the authentication system work?"

Expanded Question:
How is the authentication system implemented in the Java project, and what are its key components? Specifically, what authentication protocols or frameworks (e.g., JWT, OAuth) are used? How is user data stored and retrieved securely? Are there any custom authentication methods implemented, and how do they integrate with the standard Java security libraries?

Key Areas to Explore:
- Authentication flow and user session management
- Integration with database for user credentials
- Use of encryption for sensitive data
- Implementation of access control and user roles
- Handling of authentication failures and security logging

Potential Challenges to Consider:
- Scalability of the current authentication system
- Compliance with security standards (e.g., OWASP guidelines)
- Potential vulnerabilities in custom authentication logic
- Performance impact of the authentication process
- Compatibility with different client applications (web, mobile, API)

Now, please expand and refine the given question about the Java project.

"""



def expand_question(query_manager, original_question: str) -> str:

    # Load the expansion prompt (you can store it in a separate file)
    #with open('question_expansion_prompt.md', 'r') as file:
    #    expansion_prompt = file.read()

    # Combine the prompt with the original question
    full_prompt = f"Original Question: {original_question}\n\n{instructions_rewrite_question}"
    # print(full_prompt)
    # Query the LLM
    response = query_manager.query(full_prompt)
    # extract between <Expanded_Question> and </Expanded_Question> from the response
    expanded_question = response.split("<Expanded_Question>")[1].split("</Expanded_Question>")[0].strip()

    return expanded_question

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="rerwrite_question")
    parser.add_argument("--question", type=str, default="", required=True, help="a question about the Java code, for example 'Tell me about the package structure of the project'")
    args = parser.parse_args()
    question = args.question
    # one of task or jira should be provided
    if not question:
        print("Please provide either question or jira")
        sys.exit(1)
    # the order of the following imports is important
    # since the initialization of langfuse depends on the os environment variables
    # which are loaded in the config_utils module
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager, ResponseManager
    from llm_interaction import process_llm_response, initiate_llm_query_manager
    
    query_manager = initiate_llm_query_manager(pf=None, system_prompt=system_prompt_rewrite_question, reused_prompt_template=None)

    expanded_q = expand_question(query_manager, question)
    print("\nExpanded Question:")
    print(expanded_q)