# Java File Semantic Analysis - Phase 1

## Task Description
Analyze the provided Java file to extract its semantic meaning, purpose, and key attributes. Classify the file by type and extract relevant information based on that classification.

## File Content
```java
{file_content}
```

## Analysis Instructions

1. First, classify this file into ONE of the following categories:
   - SERVICE_IMPLEMENTATION: Implements business logic, orchestrates operations
   - SERVICE_INTERFACE: Defines a contract for services
   - CONTROLLER: Handles HTTP/API requests
   - DATA_MODEL: Represents data structures (DTOs, Entities, Value Objects)
   - CONFIGURATION: Configures application behavior
   - REPOSITORY: Provides data access
   - UTILITY: Contains helper methods
   - ENUM: Defines enumerated values
   - EXCEPTION: Represents error conditions
   - FACTORY: Creates other objects
   - OTHER: (specify if none of the above)

2. Extract the following general information:
   - Full class name including package
   - Public interfaces implemented
   - Classes extended
   - Primary responsibility (1-2 sentences)
   - Key annotations at class level

3. Based on the file classification, extract specific details:

   ### For SERVICE_IMPLEMENTATION:
   - Key dependencies injected
   - Main operations provided
   - External services called
   - Main data transformations performed
   - Error handling patterns
   - Business rules enforced

   ### For SERVICE_INTERFACE:
   - Contract methods with parameters and return types
   - Contract semantics (what this service promises to do)

   ### For CONTROLLER:
   - API endpoints exposed
   - Request parameters handled
   - Response structures returned
   - Services invoked

   ### For DATA_MODEL:
   - Key fields and their meaning
   - Validation rules
   - Relationships to other entities
   - Special serialization/deserialization handling

   ### For REPOSITORY:
   - Entity type managed
   - Query methods provided
   - Database operations supported

   ### For UTILITY:
   - Categories of utility functions
   - Stateless vs. stateful behavior
   - Thread safety characteristics

   ### For OTHER types:
   - Key functionality
   - Integration points with other components

4. Identify potential architectural patterns:
   - Design patterns implemented
   - Architectural styles (e.g., MVC, CQRS, event-driven)
   - Cross-cutting concerns (logging, security, transactions)

## Response Format
Provide your analysis in the following JSON structure:

```json
{
  "file_type": "SERVICE_IMPLEMENTATION", 
  "package": "com.example.service",
  "class_name": "ExampleServiceImpl",
  "full_path": "com.example.service.ExampleServiceImpl",
  "implements": ["ExampleService"],
  "extends": "BaseService",
  "primary_responsibility": "Manages user authentication and session handling",
  "annotations": ["@Service", "@Slf4j"],
  
  "specific_details": {
    // Fields based on file_type - leave empty sections for non-applicable categories
    "dependencies": [
      {"name": "UserRepository", "purpose": "Data access for user records"},
      {"name": "TokenService", "purpose": "JWT token generation and validation"}
    ],
    "operations": [
      {"name": "authenticate", "purpose": "Verifies user credentials and creates session"},
      {"name": "validateToken", "purpose": "Checks if token is valid and not expired"}
    ],
    "data_transformations": [
      {"from": "User", "to": "UserDTO", "context": "When returning user info to controllers"}
    ],
    "error_handling": [
      {"error": "InvalidCredentialsException", "strategy": "Returns 401 response"}
    ],
    "business_rules": [
      {"rule": "Passwords must be hashed using BCrypt", "implementation": "passwordEncoder.encode()"}
    ]
  },
  
  "architectural_patterns": {
    "design_patterns": ["Factory Method", "Strategy"],
    "architectural_styles": ["Microservice component"],
    "cross_cutting_concerns": ["Logging", "Transaction management"]
  },
  
  "imports": {
    "internal": ["com.example.model.User", "com.example.repository.UserRepository"],
    "external": ["org.springframework.stereotype.Service", "lombok.extern.slf4j.Slf4j"]
  }
}
```

Ensure your response is valid JSON. Only include fields relevant to the file type, and provide as much accurate detail as can be extracted from the code.