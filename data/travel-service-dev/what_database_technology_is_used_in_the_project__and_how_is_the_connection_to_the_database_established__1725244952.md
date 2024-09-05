Let's inspect the Java project to answer the question: What database technology is used in the project, and how is the connection to the database established?

Based on the provided information and code snippets, we can conclude the following:

1. Database Technology:
   The project uses MongoDB as its database technology. This is evident from the MongoConfig.java file in the com.iky.travel.config package and the use of MongoDB-specific classes and annotations.

2. Connection Establishment:

   a. Configuration:
   - The connection to MongoDB is established using Spring Data MongoDB, which is part of the Spring Data project.
   - The MongoConfig class is annotated with @Configuration, indicating that it provides bean definitions for the Spring container.

   b. MongoClient:
   - The MongoConfig class has a constructor that takes a MongoClient as a parameter. This MongoClient is injected by Spring's dependency injection mechanism.
   - The MongoClient is responsible for maintaining the connection pool to the MongoDB server.

   c. MongoTemplate:
   - The mongoTemplate() method in MongoConfig is annotated with @Bean, which means it provides a bean definition for MongoTemplate.
   - MongoTemplate is a helper class in Spring Data MongoDB that simplifies database operations.
   - The MongoTemplate is created using the injected MongoClient and a constant MONGO_DB_NAME.

   d. Database Name:
   - The database name is defined as a constant MONGO_DB_NAME, which is imported from com.iky.travel.constant.common.MongoConstant.

3. Repository Layer:
   - The project uses Spring Data MongoDB repositories, as evidenced by the CityRepository.java file which extends MongoRepository.
   - This provides an abstraction layer over MongoDB operations, allowing for easy CRUD operations without writing explicit queries.

4. Connection Process:
   - When the application starts, Spring's IoC container will create a MongoClient bean (the exact configuration for this is not visible in the provided code snippet, but it's typically defined in application properties or a separate configuration class).
   - The MongoClient bean is then injected into the MongoConfig class.
   - The mongoTemplate() method creates a MongoTemplate using this MongoClient and the specified database name.
   - This MongoTemplate bean becomes available for dependency injection throughout the application, allowing other components to perform MongoDB operations.

5. Missing Configuration Details:
   - We don't have visibility into the specific connection details such as host, port, or credentials. These are typically defined in application properties files (application.properties or application.yml), which are not present in the provided project structure.
   - The absence of these configuration files suggests that the connection details might be externalized or defined in a different way, possibly through environment variables or a separate configuration service.

6. Usage:
   - Other parts of the application can now autowire the MongoTemplate or use MongoDB repositories (like CityRepository) to interact with the database.
   - The CityRepository interface extends MongoRepository<City, String>, which provides basic CRUD operations for the City entity.
   - Custom methods like findByName and deleteByName are defined in the CityRepository, allowing for specific queries based on the city name.

In conclusion, the project uses MongoDB as its database technology, and the connection is established through Spring Data MongoDB. The configuration is set up in the MongoConfig class, which provides a MongoTemplate bean for database operations. The project also utilizes Spring Data MongoDB repositories for easier data access. However, the actual connection details (host, port, credentials) are not visible in the provided code, suggesting they might be externalized or defined in configuration files that are not present in the current project structure.

To get a more complete picture of the MongoDB setup, we would need to see the application properties file and any other MongoDB-related configuration classes, if they exist. These files might contain important information about the database connection settings, authentication, and other MongoDB-specific configurations.

**Next Steps**
[I need to search for keywords: <keyword>@EnableMongoRepositories</keyword>]
[I need content of files: <file>src/main/java/com/iky/travel/TravelBeApplication.java</file>]