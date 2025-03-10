# Memory Package

The memory package provides a sophisticated system for storing, retrieving, and managing conversation history and project insights using vector embeddings and SQLite storage.

## 🌟 Key Components

### 1. Memory Manager (`memory_manager.py`)
- Core class managing memory storage and retrieval
- Integrates vector embeddings with SQLite storage
- Supports multiple embedding providers (OpenAI, Gemini, SentenceTransformer)
- Handles conversation context and project insights

### 2. Memory CLI (`memory_cli.py`)
Command-line interface for memory management:
```bash
# List recent memories
memory_cli.py --project-root /path/to/project list

# Search memories
memory_cli.py --project-root /path/to/project search "authentication system"

# View specific memory
memory_cli.py --project-root /path/to/project view <memory-id>

# Export memories
memory_cli.py --project-root /path/to/project export
```

## 🔧 Features

### Vector-Based Search
- Semantic similarity search using embeddings
- Support for multiple embedding providers:
  - OpenAI embeddings
  - Google Gemini embeddings
  - Local SentenceTransformer embeddings
- Configurable similarity thresholds

### Persistent Storage
- SQLite database for metadata and relationships
- Vector store (Qdrant) for embeddings
- Efficient querying and retrieval
- Automatic cleanup of old entries

### Memory Types
- Conversation memories
- File summaries
- Package insights
- Key findings
- Code analysis results

### Context Management
- Retrieves relevant past conversations
- Maintains project-specific context
- Tracks accessed files and findings
- Supports metadata and tagging

## 📊 Data Model

### Memory Entry
```python
@dataclass
class MemoryEntry:
    entry_id: str
    project_id: str
    question: str
    answer: str
    key_findings: List[str]
    files_accessed: List[str]
    entry_type: str
    timestamp: int
    embedding_id: Optional[str]
    metadata: Dict[str, Any]
```

## 🔍 Usage Example

```python
from memory.memory_manager import MemoryManager
from embedding.embedding_config import EmbeddingConfig

# Initialize memory manager
manager = MemoryManager(
    project_root="/path/to/project",
    embedding_config=EmbeddingConfig(
        provider="sentence_transformer",
        model_name="all-MiniLM-L6-v2"
    ),
    vector_store_config={
        'qdrant': {
            'collection': 'java_assistant',
            'url': 'http://localhost:6333'
        }
    }
)

# Save a memory
entry_id = manager.save_memory(
    question="How does the authentication system work?",
    answer="The system uses JWT tokens with Redis storage...",
    key_findings=[
        "[IMPLEMENTATION_DETAIL] Uses JWT for authentication",
        "[ARCHITECTURE] Redis stores token blacklist"
    ],
    files_accessed=["auth/JwtAuthenticator.java"]
)

# Find similar memories
similar = manager.find_similar_memories(
    query="authentication mechanism",
    limit=3,
    score_threshold=0.7
)

# Get context for new conversation
context = manager.get_relevant_context(
    query="How are tokens validated?",
    limit=2,
    max_token_budget=2048
)
```

## ⚙️ Configuration

The memory system can be configured through `application.yml`:

```yaml
vector_store:
  use: qdrant
  embedding:
    provider: sentence_transformer  # or 'openai', 'gemini'
    model_name: all-MiniLM-L6-v2
    dimensionality: 384
  qdrant:
    collection: java_assistant
    url: http://localhost:6333
    api_key: optional_api_key
```

## 🧪 Testing

Comprehensive test suite available in `test_memory_manager_integration.py`:
- Basic initialization tests
- Storage operations
- Embedding provider tests
- Context retrieval tests
- Memory cleanup tests

Run tests with:
```bash
pytest memory/test_memory_manager_integration.py -v
```

## 📝 CLI Commands

### List Memories
```bash
memory_cli.py --project-root /path/to/project list --limit 10 --type conversation
```

### Search Memories
```bash
memory_cli.py --project-root /path/to/project search "authentication" --limit 5 --threshold 0.7
```

### View Memory Details
```bash
memory_cli.py --project-root /path/to/project view <memory-id>
```

### Delete Memories
```bash
memory_cli.py --project-root /path/to/project delete --id <memory-id>
memory_cli.py --project-root /path/to/project delete --all --type conversation
```

### Export Memories
```bash
memory_cli.py --project-root /path/to/project export --output memories.json
```

### Generate Summary
```bash
memory_cli.py --project-root /path/to/project summary
``` 