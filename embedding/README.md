# Embedding Package

The embedding package provides a flexible and extensible system for generating vector embeddings from text, supporting multiple embedding providers with automatic fallback mechanisms.

## 🌟 Key Components

### 1. Base Service (`embedding_service.py`)
- Defines the base interface for embedding services
- Implements common utilities like cosine similarity
- Provides consistent error handling

### 2. Provider Implementations
- **OpenAI** (`embedding_service_openai.py`): Uses OpenAI's text-embedding models
- **Gemini** (`embedding_service_gemini.py`): Integrates with Google's Gemini embedding models
- **SentenceTransformer** (`embedding_service_sentence_transformer.py`): Local embedding using HuggingFace models

### 3. Factory & Configuration
- **Factory** (`embedding_factory.py`): Creates appropriate embedding service instances
- **Config** (`embedding_config.py`): Manages embedding service configuration

## 🔧 Features

### Multiple Provider Support
- OpenAI embeddings (1536 dimensions)
- Google Gemini embeddings (768 dimensions)
- Local SentenceTransformer embeddings (384 dimensions)
- Automatic fallback to local models

### Smart Rate Limiting
- Built-in rate limiting for API-based providers
- Configurable requests per minute
- Automatic request throttling

### Batch Processing
- Efficient batch embedding generation
- Automatic text truncation
- Token limit management

## 📊 Usage Example

```python
from embedding.embedding_config import EmbeddingConfig
from embedding.embedding_factory import create_embedding_service

# Configure embedding service
config = EmbeddingConfig(
    provider="openai",  # or "gemini", "sentence_transformer"
    model_name="text-embedding-3-small",
    api_key="your-api-key"  # for OpenAI
)

# Create service
service = create_embedding_service(config)

# Generate single embedding
embedding = service.get_embedding("Your text here")

# Generate batch embeddings
texts = ["First text", "Second text", "Third text"]
embeddings = service.get_batch_embeddings(texts)

# Calculate similarity
similarity = service.cosine_similarity(embedding1, embedding2)
```

## ⚙️ Configuration

### OpenAI Configuration
```python
config = EmbeddingConfig(
    provider="openai",
    model_name="text-embedding-3-small",
    api_key="your-openai-key"
)
```

### Gemini Configuration
```python
config = EmbeddingConfig(
    provider="gemini",
    model_name="text-embedding-005",
    project_id="your-gcp-project",
    location="us-central1",
    dimensionality=768
)
```

### SentenceTransformer Configuration
```python
config = EmbeddingConfig(
    provider="sentence_transformer",
    model_name="all-MiniLM-L6-v2"
)
```

## 🧪 Testing

Comprehensive test suite available:
- `test_embedding_service.py`: Base service tests
- `test_embedding_service_gemini.py`: Gemini-specific tests
- `test_embedding_service_gemini_integration.py`: Integration tests

Run tests with:
```bash
# Run all tests
pytest embedding/test_*.py

# Run specific provider tests
pytest embedding/test_embedding_service_gemini.py
```

## 📝 Provider Details

### OpenAI
- Model: text-embedding-3-small
- Dimensions: 1536
- Rate Limit: 10 requests/minute
- Token Limit: 8191 tokens

### Gemini
- Model: text-embedding-005
- Dimensions: 768
- Rate Limit: 100 requests/minute
- Task Type: RETRIEVAL_DOCUMENT

### SentenceTransformer
- Default Model: all-MiniLM-L6-v2
- Dimensions: 384
- No rate limits (local)
- Efficient batch processing

## 🔄 Fallback Behavior

The system implements automatic fallback in this order:
1. Tries requested provider
2. Falls back to next available provider if primary fails
3. Ultimate fallback to local SentenceTransformer
4. Returns zero vector only if all options fail

## 🛠️ Error Handling

- Graceful degradation on API failures
- Automatic retry mechanisms
- Clear error logging
- Zero vector fallback for critical failures 