import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from conversation_reviewer import ConversationReviewer
def test_process_llm_response():
    response = """
        ### Analysis

        1. **Is the conversation making progress towards answering the main question? Why or why not?**
        - **Yes**, the conversation is making progress. The AI has identified several potential sources of information (configuration files, dependency management files, and code) and has conducted searches based on these sources. The AI has also received some search results, which include files that might contain relevant information about the database technology and connection management.

        2. **Are there any signs that the AI is stuck or repeating itself unnecessarily?**
        - **Yes**, there are signs that the AI might be repeating itself. The AI has suggested expanding the search to include additional configuration files and keywords, which is similar to the initial approach. This indicates a potential loop where the AI might continue to suggest broader searches without analyzing the results it already has.

        3. **If crucial information is still missing, what specific details are needed and how would they contribute to answering the main question?**
        - **Specific details needed**:
            - The content of the `application.yaml` file, as it is a common place for database configuration in Spring projects.
            - The content of the `MongoConfig.java` file, as it might indicate the use of MongoDB.
            - The content of the `pom.xml` file, as it lists dependencies that could reveal the database technology and related libraries.
        - These details would directly contribute to identifying the database technology and understanding how the connection is managed.

        4. **Evaluate the potential value of continuing the conversation versus concluding it now:**
        - **Potential benefits of gathering more information**:
            - Ensuring that all relevant configuration details are captured, which would provide a comprehensive understanding of the database technology and connection management.
        - **Risks of continuing**:
            - Redundancy and inefficiency if the AI continues to suggest broader searches without analyzing the existing results.
            - Potentially missing the opportunity to analyze the already identified files that likely contain the needed information.

        ### Recommendation

        **RECOMMENDATION: CONCLUDE**

        **REASON**: The conversation has gathered sufficient information to answer the main question. The identified files (`application.yaml`, `MongoConfig.java`, and `pom.xml`) are likely to contain the necessary details about the database technology and connection management. Further broad searches might lead to redundancy and inefficiency.

        **EFFICIENCY_SCORE: 7**

        **FINAL_ANSWER_PROMPT**:
        Based on the search results, the following files are likely to contain the necessary information about the database technology and connection management in the Java project:

        1. **`application.yaml`**: This file is commonly used in Spring projects to configure various settings, including database connections. Please provide the content of this file to analyze the database configuration.

        2. **`MongoConfig.java`**: This file suggests the use of MongoDB. Please provide the content of this file to confirm the database technology and understand how the connection is managed.

        3. **`pom.xml`**: This file lists the project's dependencies. Please provide the content of this file to identify any database-related dependencies and libraries used in the project.

        By analyzing these files, we can determine the database technology used and how the connection to the database is established and managed.

        """
    
    reviewer = ConversationReviewer(query_manager=None)
    res, final_prompt = reviewer.process_llm_response(reviewer_response=response)
    assert res, "The 'res' value should not be empty"
    assert res == "CONCLUDE", f"Expected 'CONCLUDE', but got '{res}'"
    assert final_prompt, "The 'final_prompt' should not be empty"
    assert "Based on the search results" in final_prompt, "The final_prompt should contain the expected content"
    

def test_process_llm_response2():
    response = """
### Analysis

1. **Is the conversation making progress towards answering the main question? Why or why not?**
   - Yes, the conversation is making progress. The AI has identified specific classes (`CityRepository.java` and `CityServiceImpl.java`) that interact with the database and has provided detailed analysis on these classes. The AI has also outlined the design patterns and frameworks used (e.g., Spring Data MongoDB).

2. **Are there any signs that the AI is stuck or repeating itself unnecessarily?**
   - There are no significant signs that the AI is stuck or repeating itself. The AI is methodically analyzing the identified classes and suggesting logical next steps to gather more information.

3. **If crucial information is still missing, what specific details are needed and how would they contribute to answering the main question?**
   - The AI has already identified the key classes and their roles. Additional details that could be useful include:
     - Any other repository or DAO classes that might be interacting with different parts of the database.
     - Configuration details from `application.properties` or `application.yml` to understand the database setup and any custom configurations.
     - Any other service classes that might be interacting with the identified repositories.

4. **Evaluate the potential value of continuing the conversation versus concluding it now:**
   - **Potential Benefits of Continuing:**
     - Gathering more information about other repository or DAO classes could provide a more comprehensive view of the database interaction layer.
     - Reviewing configuration files could reveal additional insights into the database setup and any custom configurations.
   - **Risks of Continuing:**
     - Redundancy and inefficiency if the additional information does not significantly contribute to the main question.
     - The conversation might become overly detailed without adding substantial value.

### Recommendation

**RECOMMENDATION: CONCLUDE**
**REASON:** The conversation has gathered sufficient information to answer the main question comprehensively. The identified classes (`CityRepository.java` and `CityServiceImpl.java`) and their roles, along with the design patterns and frameworks used, provide a clear understanding of the database interaction layer.
**EFFICIENCY_SCORE:** 8

**FINAL_ANSWER_PROMPT:**
The analysis of the Java project has identified the following key points regarding database interactions and design patterns:

1. **Classes and Interfaces Responsible for Database Interactions:**
   - `CityRepository.java`: This class is responsible for interacting with the MongoDB database. It extends `MongoRepository`, indicating the use of Spring Data MongoDB for database operations.
   - `CityServiceImpl.java`: This service class interacts with `CityRepository` to perform various operations such as adding, updating, and deleting cities. It also uses Redis for caching purposes.

2. **Design Patterns Employed:**
   - **Repository Pattern:** The `CityRepository` class follows the Repository pattern, which is a common design pattern for abstracting database interactions.
   - **Service Layer Pattern:** The `CityServiceImpl` class follows the Service Layer pattern, encapsulating business logic and coordinating between the repository and other components.

3. **Frameworks and Libraries Used:**
   - **Spring Data MongoDB:** Used for MongoDB interactions via the `MongoRepository` interface.
   - **Spring Data Redis:** Used for caching and other Redis operations.

This information provides a comprehensive understanding of the database interaction layer and the design patterns employed in the project.
    """
    reviewer = ConversationReviewer(query_manager=None)
    res, final_prompt = reviewer.process_llm_response(reviewer_response=response)
    assert res, "The 'res' value should not be empty"
    assert res == "CONCLUDE", f"Expected 'CONCLUDE', but got '{res}'"
    assert final_prompt, "The 'final_prompt' should not be empty"
    print(final_prompt)
