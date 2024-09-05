Let's inspect the Java project to answer the question: What database technology is used in the project, and how is the connection to the database established?

Based on the provided information, we can identify that this project uses two database technologies:

1. MongoDB
2. Redis

Let's analyze each of these in detail:

1. MongoDB:
MongoDB is used as the primary database for storing data in this project. This is evident from the MongoConfig.java file in the com.iky.travel.config package.

Key points about MongoDB configuration:
- The project uses Spring Data MongoDB for integration.
- A MongoTemplate bean is configured in the MongoConfig class.
- The MongoDB connection is established using a MongoClient, which is injected into the MongoConfig constructor.
- The database name is defined in the MongoConstant class as MONGO_DB_NAME with the value "travel".

How the connection is established:
- The MongoClient is automatically configured by Spring Boot's auto-configuration feature. This is inferred because the MongoClient is injected into the MongoConfig constructor without explicit configuration in this file.
- The MongoTemplate is created using the injected MongoClient and the database name.
- The MongoConfig class is annotated with @Configuration, indicating that it provides bean definitions for the Spring container.
- The mongoTemplate() method is annotated with @Bean, which means Spring will manage this bean and make it available for dependency injection throughout the application.

2. Redis:
Redis is used as a caching layer or for storing temporary data. This is evident from the RedisConfig.java file in the com.iky.travel.config package.

Key points about Redis configuration:
- The project uses Spring Data Redis for integration.
- A RedisTemplate bean is configured in the RedisConfig class.
- The Redis connection is established using a RedisConnectionFactory, which is injected into the redisTemplate method.
- Redis keys for city data and popular destinations are defined in the RedisConstant class.

How the connection is established:
- The RedisConnectionFactory is automatically configured by Spring Boot's auto-configuration feature. This is inferred because the RedisConnectionFactory is injected into the redisTemplate method without explicit configuration in this file.
- The RedisTemplate is created and configured with serializers for keys (StringRedisSerializer) and values (GenericJackson2JsonRedisSerializer).
- The RedisConfig class is annotated with @Configuration, indicating that it provides bean definitions for the Spring container.
- The redisTemplate() method is annotated with @Bean, which means Spring will manage this bean and make it available for dependency injection throughout the application.

Additional observations:
1. The project structure suggests a well-organized, modular approach to database configuration.
2. The use of separate configuration classes for MongoDB and Redis allows for clear separation of concerns and easier maintenance.
3. The project leverages Spring Boot's auto-configuration capabilities, which simplifies the setup process for both databases.
4. Constants related to MongoDB and Redis are stored in separate constant classes (MongoConstant.java and RedisConstant.java) in the com.iky.travel.constant.common package, promoting better organization and maintainability of configuration values.

It's worth noting that we don't have access to the application.properties or application.yml files, which would typically contain specific connection details such as hostnames, ports, and authentication information for both MongoDB and Redis. These details are likely managed through environment variables or external configuration files for security reasons.

In conclusion, this project uses a combination of MongoDB as the primary database and Redis as a caching or temporary data store. The connections to both databases are primarily managed by Spring Boot's auto-configuration, with additional custom configuration provided in the MongoConfig and RedisConfig classes. This setup allows for flexible and efficient data management, with MongoDB handling persistent storage and Redis providing fast in-memory data access for improved performance.



[I need to search for keywords: <keyword>spring.data.redis</keyword>]