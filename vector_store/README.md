# Vector Store Package

This package provides a vector database integration layer, primarily focused on Qdrant vector database operations for storing and retrieving embeddings with associated metadata.

## Components

### Vector Store Client (`vector_store_client.py`)
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

### Configuration

Create an `application.yml` file with the following structure:

```yaml
vector_store:
  use: qdrant
  embedding_provider: openai  # Options: openai, gemini, auto
  qdrant:
    api_key: your_api_key
    url: your_qdrant_url
    collection: collection_name
```

## Usage Examples

### Basic Initialization and Operations

```python
from vector_store.vector_store_client import QdrantVectorStore
from vector_store.vector_store_config import load_vector_store_config

# Initialize vector store
vector_store = QdrantVectorStore(
    collection_name="your_collection",
    vector_size=1536  # Adjust based on your embedding model
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

### Using with Embedding Services

```python
from embedding.embedding_factory import get_embedding_service
from vector_store.vector_store_client import QdrantVectorStore

# Get embedding service
embedding_service = get_embedding_service("openai")  # or "gemini"

# Create embeddings
text = "This is a sample document"
embedding = embedding_service.get_embedding(text)

# Store in vector database
vector_store = QdrantVectorStore(collection_name="my_collection")
vector_store.store_embedding(
    vector=embedding,
    text=text,
    metadata={"project_id": "project_1", "entry_type": "document"}
)
```

## Testing
Run tests using pytest:
```bash
# Run all tests
pytest vector_store/
```

## Dependencies
- qdrant-client
- pyyaml
- numpy
- pytest (for testing)
- openai (for OpenAI embeddings)
- google-generativeai (for Gemini embeddings)

## Notes
- The package supports both local (in-memory) and cloud Qdrant instances
- Vector size depends on the embedding model used:
  - OpenAI embeddings: 1536 dimensions
  - Gemini embeddings: 768 dimensions
- Cosine similarity is used for vector comparisons
- Automatic payload indexing for efficient filtering
- Configuration can be loaded from custom paths using `load_vector_store_config(config_path)`
- Default values are provided if configuration is missing
