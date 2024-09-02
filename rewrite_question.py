import argparse
import sys
from typing import List, Tuple


system_prompt_rewrite_question = """
You are an AI assistant designed to help expand and refine questions about Java projects. 
"""

instructions_rewrite_question = """
You are an expert in analyzing Java projects and breaking down complex questions into smaller, more manageable parts. Your task is to take an initial question about a Java project, decompose it into a series of smaller, interconnected questions, and then provide a refined version of the original question based on this decomposition.

## Context
- The question is about a Java project that has been summarized for quick reference.
- The decomposed questions will be used to query a knowledge base of Java file summaries and project structure.
- The goal is to create a step-by-step analysis that helps developers thoroughly understand and maintain complex projects.

## Instructions
1. Analyze the given question and break it down into 3-7 smaller, more focused questions.
2. Ensure each sub-question is specific, clear, and directly related to the original inquiry.
3. Order the questions logically, so that each builds upon the information gathered from the previous ones.
4. Focus on exploring both high-level architecture and low-level implementation details.
5. Include questions that address:
   - Project structure and architecture
   - Data flow and processing steps
   - Specific code components (classes, methods, interfaces)
   - Integration with databases, external systems, or libraries
   - Error handling and performance considerations
6. Avoid questions about improvements or optimizations unless directly related to the original inquiry.
7. Use specific Java-related terminologies and concepts relevant to the question.
8. After decomposing the question, create a refined version of the original question that encompasses all aspects covered by the sub-questions.

## Output Format
Provide your response in the following format:

Original Question: [Insert the original question here]

<Decomposed_Questions>
1. [First sub-question]
2. [Second sub-question]
3. [Third sub-question]
...
</Decomposed_Questions>

<Refined_Question>
[Provide a refined and more comprehensive version of the original question, taking into account all aspects covered by the sub-questions]
</Refined_Question>

<Analysis_Approach>
[Briefly explain how answering these questions in sequence will provide a comprehensive understanding of the original inquiry. Mention any potential challenges or areas that might require special attention.]
</Analysis_Approach>

## Example
Original Question: "How does the Java project interact with the database to retrieve and process user data?"

<Decomposed_Questions>
1. What database technology is used, and how is the connection to the database established and managed in the Java project?
2. Which classes or interfaces are responsible for database interactions, and what design patterns are employed (e.g., DAO, Repository)?
3. How are database queries constructed and executed? Are there any query builders or ORM frameworks in use?
4. What data models or DTOs are used to represent user data within the Java application?
5. How is the retrieved data processed, transformed, or validated before being used in the application logic?
6. What error handling mechanisms are in place for database operations, and how are connection issues or query failures managed?
7. Are there any performance optimization techniques implemented for database interactions, such as connection pooling or caching?
</Decomposed_Questions>

<Refined_Question>
What is the complete architecture and process flow of database interactions in the Java project, including the technology stack, design patterns, query construction, data modeling, processing steps, error handling, and optimization techniques used for retrieving and processing user data?
</Refined_Question>

<Analysis_Approach>
This sequence of questions allows for a systematic exploration of the database interaction process, starting from the connection setup, moving through the data access layer, and ending with error handling and optimization techniques. By answering these questions in order, we'll gain a comprehensive understanding of how user data flows through the system, from database retrieval to application use. The refined question encapsulates all these aspects, providing a holistic view of the database interaction system. Special attention should be paid to the data access layer architecture and any custom implementations that might deviate from standard practices.
</Analysis_Approach>

Now, please decompose the given question about the Java project into a series of smaller, focused questions, and provide a refined version of the original question.

"""



def decompose_question(query_manager, original_question: str) -> Tuple[List[str], str]:

    full_prompt = f"{instructions_rewrite_question}\n\nOriginal Question: {original_question}"

    # Query the LLM
    response = query_manager.query(full_prompt)

    decomposed_questions = response.split("<Decomposed_Questions>")[1].split("</Decomposed_Questions>")[0].strip()
    # get the list of decomposed questions, remove the 1. 2. 3. etc.
    decomposed_questions_list = [dq.split(". ")[1] for dq in decomposed_questions.split("\n") if dq.strip()]
    
    # extract between <Refined_Question> and </Refined_Question> from the response
    refined_question = response.split("<Refined_Question>")[1].split("</Refined_Question>")[0].strip()
    return decomposed_questions_list, refined_question

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

    decomposed_questions_list, refined_question = decompose_question(query_manager, question)
    print("\ndecomposed_questions_list:", decomposed_questions_list)
    print("\nrefined_question:", refined_question)
