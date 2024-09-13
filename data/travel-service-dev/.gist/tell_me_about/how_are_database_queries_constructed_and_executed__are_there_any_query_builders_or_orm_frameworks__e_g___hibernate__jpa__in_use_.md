### How are database queries constructed and executed? Are there any query builders or ORM frameworks (e.g., Hibernate, JPA) in use?

#### Key Findings:

1. **Redis Configuration:**
   - The `RedisConfig.java` file configures a `RedisTemplate` for interacting with Redis. This indicates that Redis is used for caching or temporary storage.

2. **City Service Implementation:**
   - The `CityServiceImpl.java` file contains methods for adding, updating, and deleting city records. It uses both Redis and MongoDB (`CityRepository`) for these operations. Redis is used for caching city data, while MongoDB is used for persistent storage.

3. **City Repository:**
   - The `CityRepository.java` file extends `MongoRepository`, indicating that MongoDB is used for persistent storage of city data. The repository provides methods for finding and deleting city records by name.

4. **Travel Service Implementation:**
   - The `TravelServiceImpl.java` file contains methods for retrieving and clearing popular destinations, using Redis for these operations.

5. **Exception Handling:**
   - The exception handling files (`ApiExceptionHandler.java`, `CityUpdateException.java`, `CityDeleteException.java`) provide custom exceptions and handlers for various city-related operations, ensuring robust error handling during database interactions.

#### Detailed Analysis:

1. **Redis Configuration:**
   - The `RedisConfig.java` file sets up a `RedisTemplate` with custom serializers for keys and values. This template is used throughout the application to interact with Redis.
   ```java
   @Configuration
   public class RedisConfig {
     @Bean
     public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
       RedisTemplate<String, Object> template = new RedisTemplate<>();
       template.setConnectionFactory(connectionFactory);
       template.setKeySerializer(new StringRedisSerializer());
       template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
       return template;
     }
   }
   ```

2. **City Service Implementation:**
   - The `CityServiceImpl.java` file shows how city data is managed. It uses `CityRepository` for MongoDB operations and `RedisTemplate` for Redis operations.
   - Adding a city involves saving the city to MongoDB and caching it in Redis.
   - Updating a city involves checking its existence, updating it in MongoDB, and updating the cache in Redis.
   - Deleting a city involves removing it from both MongoDB and Redis.
   ```java
   @Service
   public class CityServiceImpl implements CityService {
     private final RedisTemplate<String, Object> redisTemplate;
     private final HashOperations<String, String, CityDTO> hashOperations;
     private final CityRepository cityRepository;

     public CityServiceImpl(CityRepository cityRepository, RedisTemplate<String, Object> redisTemplate) {
       this.cityRepository = cityRepository;
       this.redisTemplate = redisTemplate;
       this.hashOperations = redisTemplate.opsForHash();
     }

     @Override
     public boolean addCity(CityDTO cityDTO) {
       if (cityExists(cityDTO.getName())) {
         throw new CityAlreadyExistsException("City Already Exists: " + cityDTO.getName());
       }
       City city = CityMapper.INSTANCE.dtoToCity(cityDTO);
       cityRepository.save(city);
       hashOperations.put(generateRedisKey(city.getName()), city.getName(), cityDTO);
       return true;
     }

     @Override
     public boolean updateCity(CityDTO updatedCity) {
       if (!cityExists(updatedCity.getName())) {
         throw new CityNotFoundException("City to update not found: " + updatedCity.getName());
       }
       City city = CityMapper.INSTANCE.dtoToCity(updatedCity);
       cityRepository.save(city);
       hashOperations.put(generateRedisKey(city.getName()), city.getName(), updatedCity);
       return true;
     }

     @Override
     public boolean cityExists(String cityName) {
       if (Boolean.TRUE.equals(hashOperations.hasKey(generateRedisKey(cityName), cityName))) {
         return true;
       }
       return cityRepository.findByName(cityName).isPresent();
     }

     @Override
     public Optional<CityDTO> getCity(String cityName) {
       CityDTO cityDTO = hashOperations.get(generateRedisKey(cityName), cityName);
       if (cityDTO != null) {
         incrementCityQueryCount(cityName);
         return Optional.of(cityDTO);
       }
       Optional<City> optionalCity = cityRepository.findByName(cityName);
       if (optionalCity.isPresent()) {
         cityDTO = CityMapper.INSTANCE.cityToDto(optionalCity.get());
         hashOperations.put(generateRedisKey(cityName), cityName, cityDTO);
         incrementCityQueryCount(cityName);
         return Optional.of(cityDTO);
       }
       return Optional.empty();
     }

     @Override
     public boolean deleteCity(String cityName) {
       try {
         hashOperations.delete(generateRedisKey(cityName), cityName);
         cityRepository.deleteByName(cityName);
       } catch (Exception ex) {
         throw new CityDeleteException("Error when deleting city:" + cityName, ex);
       }
       return false;
     }

     public void incrementCityQueryCount(String cityName) {
       redisTemplate.opsForZSet().incrementScore("popularDestinations", cityName, 1);
     }

     private String generateRedisKey(String cityName) {
       return CITY_KEY + ":" + cityName;
     }
   }
   ```

3. **City Repository:**
   - The `CityRepository.java` file extends `MongoRepository`, providing CRUD operations for the `City` entity.
   ```java
   @Repository
   public interface CityRepository extends MongoRepository<City, String> {
     Optional<City> findByName(String name);
     boolean deleteByName(String name);
   }
   ```

4. **Travel Service Implementation:**
   - The `TravelServiceImpl.java` file shows how popular destinations are managed using Redis.
   - It retrieves the most queried cities and clears the list of popular destinations.
   ```java
   @Service
   public class TravelServiceImpl implements TravelService {
     private final RedisTemplate<String, Object> redisTemplate;

     public TravelServiceImpl(RedisTemplate<String, Object> redisTemplate) {
       this.redisTemplate = redisTemplate;
     }

     @Override
     public Set<Object> getMostQueriedCities(int topN) {
       return redisTemplate.opsForZSet().reverseRange(POPULAR_DESTINATIONS_KEY, 0, (long) topN - 1);
     }

     public Set<Object> getAllCities() {
       Set<String> keys = Optional.ofNullable(redisTemplate.keys(CITY_KEY + ":*"))
           .orElseGet(Collections::emptySet);

       return keys.stream()
           .flatMap(key -> redisTemplate.opsForHash().entries(key).values().stream())
           .filter(Objects::nonNull)
           .collect(Collectors.toSet());
     }

     @Override
     public boolean clearPopularDestinations() {
       return Boolean.TRUE.equals(redisTemplate.delete(POPULAR_DESTINATIONS_KEY));
     }
   }
   ```

5. **Exception Handling:**
   - The `ApiExceptionHandler.java` file provides custom exception handlers for various city-related operations, ensuring robust error handling during database interactions.
   ```java
   @RestControllerAdvice
   public class ApiExceptionHandler {
     @ExceptionHandler(CityNotFoundException.class)
     public ResponseEntity<ApiErrorResponse> cityNotFoundHandler(CityNotFoundException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime.now(),
           HttpStatus.NOT_FOUND.value(),
           "City Not Found",
           ex.getMessage(),
           request.getDescription(false).replace("uri=", "")
       );
       return new ResponseEntity<>(error, HttpStatus.NOT_FOUND);
     }

     @ExceptionHandler(CityAlreadyExistsException.class)
     public ResponseEntity<ApiErrorResponse> cityAlreadyExistHandler(CityAlreadyExistsException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime.now(),
           HttpStatus.BAD_REQUEST.value(),
           "City Already Exists",
           ex.getMessage(),
           request.getDescription(false).replace("uri=", "")
       );
       return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
     }

     @ExceptionHandler(CityAddException.class)
     public ResponseEntity<ApiErrorResponse> cityAddExceptionHandler(CityAddException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime.now(),
           HttpStatus.BAD_REQUEST.value(),
           "City Add Exception",
           ex.getMessage(),
           request.getDescription(false).replace("uri=", "")
       );
       return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
     }

     @ExceptionHandler(CityUpdateException.class)
     public ResponseEntity<ApiErrorResponse> cityUpdateExceptionHandler(CityUpdateException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime.now(),
           HttpStatus.BAD_REQUEST.value(),
           "City Update Exception",
           ex.getMessage(),
           request.getDescription(false).replace("uri=", "")
       );
       return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
     }

     @ExceptionHandler(CityDeleteException.class)
     public ResponseEntity<ApiErrorResponse> cityDeleteExceptionHandler(CityDeleteException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime.now(),
           HttpStatus.BAD_REQUEST.value(),
           "City Delete Exception",
           ex.getMessage(),
           request.getDescription(false).replace("uri=", "")
       );
       return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
     }

     @ExceptionHandler(RedisException.class)
     public ResponseEntity<ApiErrorResponse> cityUpdateExceptionHandler(RedisException ex, WebRequest request) {
       ApiErrorResponse error = new ApiErrorResponse(
           LocalDateTime