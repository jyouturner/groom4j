# Vector Store Package

This package provides a vector database integration layer, primarily focused on Qdrant vector database operations for storing and retrieving embeddings with associated metadata.

## Components

### 1. Vector Store Client (`vector_store_client.py`)
The main implementation of vector database operations using Qdrant:
- Supports both cloud and local in-memory Qdrant instances
- Handles vector storage, retrieval, and similarity search
- Manages metadata indexing and filtering
- Provides CRUD operations for embeddings and their associated data

Key features:
- Vector similarity search with configurable thresholds
- Metadata filtering by project ID and entry type
- Batch operations support
- Automatic collection initialization and validation

### 2. Vector Store Config (`vector_store_config.py`)
Manages configuration for vector store operations:
- Loads configuration from YAML files
- Sets up environment variables
- Provides default configurations
- Handles configuration updates

### 3. Tests
Comprehensive test suite including:
- Unit tests for configuration management
- Integration tests for vector store operations
- Cloud-specific tests for Qdrant operations

## Usage

### Basic Configuration
Create an `application.yml` file with the following structure:

```yaml
vector_store:
  use: qdrant
  embedding_provider: auto
  qdrant:
    api_key: your_api_key
    url: your_qdrant_url
    collection: collection_name
```

### Code Example
```python
from vector_store.vector_store_client import QdrantVectorStore
from vector_store.vector_store_config import load_vector_store_config

# Load configuration
config = load_vector_store_config()

# Initialize vector store
vector_store = QdrantVectorStore(
    collection_name="your_collection",
    vector_size=384  # Adjust based on your embedding size
)

# Store an embedding
entry_id = vector_store.store_embedding(
    vector=[0.1, 0.2, ...],  # Your vector embedding
    text="Document text",
    metadata={
        "project_id": "project_123",
        "entry_type": "document",
        "timestamp": 1234567890
    }
)

# Search similar vectors
results = vector_store.search_similar(
    query_vector=[0.1, 0.2, ...],
    project_id="project_123",
    limit=5,
    score_threshold=0.75
)
```

## Environment Variables
- `QDRANT_URL`: URL for Qdrant server
- `QDRANT_API_KEY`: API key for Qdrant authentication
- `VECTOR_STORE_USE`: Vector store provider (defaults to 'qdrant')
- `EMBEDDING_PROVIDER`: Embedding provider to use
- `QDRANT_COLLECTION`: Default collection name

## Testing
Run tests using pytest:
```bash
# Run all tests
pytest vector_store/

# Run only integration tests
pytest vector_store/ -m integration

# Run specific test file
pytest vector_store/test_vector_store_client.py
```

## Dependencies
- qdrant-client
- pyyaml
- numpy
- pytest (for testing)

## Notes
- The package supports both local (in-memory) and cloud Qdrant instances
- Default vector size is 384 dimensions
- Cosine similarity is used for vector comparisons
- Automatic payload indexing for efficient filtering
- Configuration can be loaded from custom paths using `load_vector_store_config(config_path)`
- Default values are provided if configuration is missing

