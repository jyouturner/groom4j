Let's inspect the Java project to answer the question: What database technology is used in the project, and how is the connection to the database established?

Based on the provided information and the additional materials, we can conclude that the project uses MongoDB as its database technology. Let's analyze how the connection to the database is established:

1. Database Technology:
   The project uses MongoDB, which is a NoSQL document database. This is confirmed by the presence of MongoDB-specific classes and configurations in the project structure.

2. Connection Establishment:
   The connection to the MongoDB database is established through Spring Data MongoDB, which is a part of the larger Spring Data project. Here's how it's set up:

   a. MongoDB Configuration:
      - The `MongoConfig` class (in `src/main/java/com/iky/travel/config/MongoConfig.java`) is responsible for configuring the MongoDB connection.
      - It's annotated with `@Configuration`, indicating that it provides bean definitions for the Spring application context.

   b. MongoDB Client:
      - The `MongoConfig` class has a constructor that takes a `MongoClient` as a parameter.
      - This `MongoClient` is likely automatically configured and injected by Spring Boot's auto-configuration mechanism.
      - The exact connection details (host, port, credentials) are not visible in the provided code, but they are typically specified in the application's properties file (e.g., application.properties or application.yml).

   c. MongoTemplate Configuration:
      - The `MongoConfig` class defines a `@Bean` method called `mongoTemplate()` which creates and returns a `MongoTemplate` instance.
      - The `MongoTemplate` is instantiated with the injected `MongoClient` and a database name.
      - The database name is defined as a constant `MONGO_DB_NAME` in the `MongoConstant` class (in `src/main/java/com/iky/travel/constant/common/MongoConstant.java`).
      - The value of `MONGO_DB_NAME` is set to "travel".

   d. Usage:
      - The `MongoTemplate` bean created in the `MongoConfig` class is the primary interface for MongoDB operations in the application.
      - It can be injected into other components (like services or repositories) to perform database operations.

3. Repository Layer:
   - The `CityRepository` interface extends `MongoRepository<City, String>`, which is a Spring Data MongoDB interface.
   - This provides a high-level abstraction for database operations on the `City` entity.
   - Custom methods like `findByName` and `deleteByName` are defined in this interface, which Spring Data MongoDB will implement automatically based on the method names.

4. Entity Mapping:
   - The `City` class is annotated with `@Document(collection = "cities")`, indicating that it represents a document in the "cities" collection in MongoDB.
   - Fields are mapped to MongoDB document properties, with some using `@Field` annotations for custom naming (e.g., `@Field("plate_no")` for `plateNo`).
   - The `@Id` annotation is used to mark the primary key field.

In conclusion, the project uses MongoDB as its database technology, with the connection established through Spring Data MongoDB. The `MongoConfig` class plays a crucial role in setting up the `MongoTemplate`, which is the main component for interacting with the MongoDB database. The database name is set to "travel" and is defined in the `MongoConstant` class.

The actual connection details (such as host, port, and credentials) are not visible in the provided code snippets. These details are typically externalized in configuration files (like application.properties or application.yml) following best practices for application configuration management.

To get a more comprehensive understanding of the database setup, it would be helpful to examine the contents of the application properties file, as it might contain additional configuration details such as connection string, authentication information, and other MongoDB-specific settings. However, we don't have access to these files in the provided project structure.



[I need to search for keywords: <keyword>application.properties</keyword>, <keyword>application.yml</keyword>]