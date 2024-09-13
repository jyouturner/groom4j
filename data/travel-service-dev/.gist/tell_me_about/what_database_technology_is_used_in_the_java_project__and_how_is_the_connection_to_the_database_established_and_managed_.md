### Database Technology and Connection Management in the Java Project

#### Database Technology
The Java project uses **MongoDB** as its database technology. This is evident from the configuration and repository files provided.

#### Connection Establishment and Management

1. **Configuration File: `MongoConfig.java`**
   - **Package**: `com.iky.travel.config`
   - **Purpose**: This file is responsible for configuring the connection to the MongoDB database.
   - **Key Components**:
     - **MongoClient**: The `MongoClient` instance is injected into the configuration class. This client is used to interact with the MongoDB server.
     - **MongoTemplate**: A `MongoTemplate` bean is defined, which is a Spring Data abstraction for MongoDB operations. It is initialized with the `MongoClient` and the database name (`MONGO_DB_NAME`).

   ```java
   package com.iky.travel.config;

   import static com.iky.travel.constant.common.MongoConstant.MONGO_DB_NAME;

   import com.mongodb.client.MongoClient;
   import org.springframework.context.annotation.Bean;
   import org.springframework.context.annotation.Configuration;
   import org.springframework.data.mongodb.core.MongoTemplate;

   @Configuration
   public class MongoConfig {

     private final MongoClient mongoClient;

     public MongoConfig(MongoClient mongoClient) {
       this.mongoClient = mongoClient;
     }

     @Bean
     public MongoTemplate mongoTemplate() {
       return new MongoTemplate(mongoClient, MONGO_DB_NAME);
     }
   }
   ```

2. **Repository File: `CityRepository.java`**
   - **Package**: `com.iky.travel.domain.repository.city`
   - **Purpose**: This file defines a repository interface for performing CRUD operations on the `City` collection in MongoDB.
   - **Key Components**:
     - **MongoRepository**: The `CityRepository` interface extends `MongoRepository`, which provides generic CRUD operation methods.
     - **Custom Methods**: Additional methods like `findByName` and `deleteByName` are defined for specific queries.

   ```java
   package com.iky.travel.domain.repository.city;

   import com.iky.travel.domain.model.City;
   import java.util.Optional;
   import org.springframework.data.mongodb.repository.MongoRepository;
   import org.springframework.stereotype.Repository;

   @Repository
   public interface CityRepository extends MongoRepository<City, String> {

     Optional<City> findByName(String name);

     boolean deleteByName(String name);
   }
   ```

### Summary
- **Database Technology**: MongoDB
- **Connection Management**:
  - The connection to MongoDB is configured in the `MongoConfig.java` file using a `MongoClient` and `MongoTemplate`.
  - Data access and manipulation are handled through the `CityRepository.java` file, which extends `MongoRepository` to leverage Spring Data MongoDB's capabilities.

This setup ensures efficient and streamlined interaction with the MongoDB database, utilizing Spring's data access abstractions.