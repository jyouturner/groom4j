import os
import sys
import pytest
import tempfile
from pathlib import Path
import shutil
import yaml
import time
import uuid
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import your modules
from embedding.embedding_service_sentence_transformer import SentenceTransformerEmbeddingService
from memory_manager import MemoryManager, SQLiteStorage, MemoryEntry
from vector_store.vector_store_client import QdrantVectorStore
from embedding.embedding_factory import create_embedding_service
from embedding.embedding_config import EmbeddingConfig
from embedding.embedding_service_openai import OpenAiEmbeddingService
from embedding.embedding_service_gemini import GeminiEmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration from environment variables
QDRANT_URL = os.getenv("TEST_QDRANT_URL", "")
QDRANT_COLLECTION = os.getenv("TEST_QDRANT_COLLECTION", "test_collection")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")

# Skip markers based on available services
requires_qdrant = pytest.mark.skipif(
    not QDRANT_URL,
    reason="Qdrant URL not configured, skipping test. Try: export TEST_QDRANT_URL=https://..."
)

requires_openai = pytest.mark.skipif(
    not OPENAI_API_KEY,
    reason="OpenAI API key not configured"
)

requires_gemini = pytest.mark.skipif(
    not GCP_PROJECT_ID,
    reason="GCP project ID not configured"
)

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .gist directory
        gist_dir = Path(temp_dir) / ".gist"
        gist_dir.mkdir(exist_ok=True)
        
        # Create a test application.yml with environment-based configuration
        config = {
            'vector_store': {
                'use': 'qdrant',
                'embedding_provider': 'auto',
                'embedding': {
                    'model_name': 'all-MiniLM-L6-v2'  # Add this for SentenceTransformer
                },
                'qdrant': {
                    'collection': 'test_collection',
                    'url': None  # Use in-memory for testing
                }
            }
        }
        
        # Create application.yml in the temp directory
        config_path = Path(temp_dir) / "application.yml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
            
        yield temp_dir

@pytest.fixture
def test_data():
    """Fixture providing test data"""
    return {
        "question": "How does the authentication system work in this Java project?",
        "answer": "The authentication system uses JWT tokens with a custom validation mechanism.",
        "key_findings": [
            "[IMPLEMENTATION_DETAIL] Uses JWT for authentication tokens",
            "[ARCHITECTURE] Authentication is handled by a separate microservice",
            "[SECURITY] Tokens expire after 24 hours"
        ],
        "files_accessed": ["src/main/java/com/example/auth/JwtAuthenticator.java"]
    }

@pytest.fixture
def memory_manager(temp_project_dir):
    """Create a memory manager for testing"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        project_id="test-project",
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                'url': None  # Use in-memory for testing
            }
        }
    )
    return manager

@pytest.mark.integration
def test_memory_manager_basic_initialization(temp_project_dir):
    """Test basic MemoryManager initialization"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                # user local qdrant instance
                #'url': "http://localhost:6333",
                #'api_key': "any_api_key"
            }
        }  
    )
    
    # Get the active embedding service
    service = manager.get_embedding_service()
    assert service is not None, "No embedding service available"
    assert isinstance(service, SentenceTransformerEmbeddingService), "Expected SentenceTransformerEmbeddingService"
    assert manager.vector_store is not None, "No vector store available"

@pytest.mark.integration
@requires_openai
def test_memory_manager_openai_initialization(temp_project_dir):
    """Test MemoryManager initialization with OpenAI"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="openai", model_name="text-embedding-3-small", api_key=OPENAI_API_KEY),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    assert manager.embedding_service is not None
    assert isinstance(manager.embedding_service, OpenAiEmbeddingService)

@pytest.mark.integration
@requires_gemini
def test_memory_manager_gemini_initialization(temp_project_dir):
    """Test MemoryManager initialization with Gemini"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(
            provider="gemini", 
            model_name="text-embedding-005",
            project_id=GCP_PROJECT_ID
        ),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    assert manager.embedding_service is not None
    assert isinstance(manager.embedding_service, GeminiEmbeddingService)

@pytest.mark.integration
@requires_qdrant
def test_memory_storage_with_embeddings(temp_project_dir):
    """Test storing and retrieving memories with embeddings using SentenceTransformer"""

    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config = {
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    
    # Verify we have an embedding service
    embedding_service = manager.get_embedding_service()
    assert embedding_service is not None, "No embedding service available"
    assert isinstance(embedding_service, SentenceTransformerEmbeddingService)
    
    # Verify vector store dimensions match SentenceTransformer
    assert manager.vector_store.vector_size == 384, "Vector store dimensions don't match SentenceTransformer"
    
    # Test saving a memory
    test_question = "What is the purpose of the MemoryManager class?"
    test_answer = "The MemoryManager class handles storage and retrieval of conversation context using vector embeddings."
    test_findings = ["Supports multiple embedding providers", "Uses vector store for similarity search"]
    
    entry_id = manager.save_memory(
        question=test_question,
        answer=test_answer,
        key_findings=test_findings
    )
    
    assert entry_id is not None, "Failed to save memory"
    
    # Test retrieving similar memories
    similar_memories = manager.find_similar_memories(
        query="How does the memory manager work?",
        limit=1
    )
    
    assert len(similar_memories) > 0, "No similar memories found"
    assert similar_memories[0]["entry"]["question"] == test_question
    assert similar_memories[0]["similarity_score"] > 0.5

@pytest.mark.integration
def test_explicit_sentence_transformer(temp_project_dir):
    """Test explicitly requesting SentenceTransformer"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    
    service = manager.get_embedding_service()
    assert isinstance(service, SentenceTransformerEmbeddingService), "Failed to use SentenceTransformer when explicitly requested"
    
    # Test saving and retrieving with SentenceTransformer
    entry_id = manager.save_memory(
        question="Test question",
        answer="Test answer"
    )
    assert entry_id is not None, "Failed to save memory with SentenceTransformer"

def test_memory_context_retrieval(temp_project_dir):
    """Test retrieving relevant context for conversations"""

    
    # Initialize manager with explicit configuration
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config= {
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    
    # Save multiple related memories
    memories = [
        {
            "question": "How do I implement a vector store?",
            "answer": "You can use Qdrant or other vector databases...",
            "findings": ["Vector stores support similarity search", "Need embedding service"]
        },
        {
            "question": "What embedding models are supported?",
            "answer": "We support OpenAI, Gemini, and Sentence Transformers...",
            "findings": ["Multiple embedding providers", "Automatic fallback"]
        }
    ]
    
    for memory in memories:
        manager.save_memory(
            question=memory["question"],
            answer=memory["answer"],
            key_findings=memory["findings"]
        )
    
    # Test getting relevant context
    context = manager.get_relevant_context(
        query="Tell me about embedding services",
        limit=2
    )
    
    assert context != "", "No context retrieved"
    assert "embedding" in context.lower(), "Retrieved context not relevant to query"

def test_memory_cleanup(temp_project_dir):
    """Test memory cleanup operations"""
    manager = MemoryManager(
        project_root=temp_project_dir,
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config={
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    # Save a test memory
    entry_id = manager.save_memory(
        question="Test question",
        answer="Test answer"
    )
    
    # Delete the memory
    assert manager.delete_memory(entry_id), "Failed to delete memory"
    
    # Verify memory is deleted
    assert manager.get_memory_by_id(entry_id) is None, "Memory still exists after deletion"
    
    # Test clearing all memories
    manager.save_memory(
        question="Another test",
        answer="Another answer"
    )
    
    assert manager.clear_project_memories(), "Failed to clear project memories"
    
    recent_memories = manager.get_recent_memories()
    assert len(recent_memories) == 0, "Memories still exist after clearing"

def test_sqlite_storage_basic(temp_project_dir, test_data):
    """Test basic SQLite storage functionality"""
    # Initialize SQLite storage
    db_path = Path(temp_project_dir) / ".gist" / "test_memory.db"
    storage = SQLiteStorage(db_path=str(db_path))
    
    # Test project saving
    result = storage.save_project(
        project_id="test-project",
        project_name="Test Project",
        root_path=temp_project_dir
    )
    assert result, "Failed to save project"
    
    # Create and save test entry
    entry_id = str(uuid.uuid4())
    # Make a deep copy of the test data's key findings to avoid modifying the original
    original_key_findings = test_data["key_findings"].copy()
    
    test_entry = MemoryEntry(
        entry_id=entry_id,
        project_id="test-project",
        question=test_data["question"],
        answer=test_data["answer"],
        key_findings=original_key_findings,
        files_accessed=test_data["files_accessed"],
        entry_type="conversation",
        timestamp=int(time.time()),
        metadata={"test": True}
    )
    
    # Test CRUD operations
    assert storage.save_entry(test_entry), "Failed to save entry"
    
    retrieved_entry = storage.get_entry(entry_id)
    assert retrieved_entry is not None, "Failed to retrieve entry"
    assert retrieved_entry.question == test_data["question"]
    
    # Test update - add a new key finding, not one that's already in test_data
    original_count = len(retrieved_entry.key_findings)
    test_entry.key_findings.append("[NEW_RULE] Maximum token lifetime is 24 hours")
    assert storage.save_entry(test_entry), "Failed to update entry"
    
    updated_entry = storage.get_entry(entry_id)
    assert len(updated_entry.key_findings) == original_count + 1, "Key finding not added correctly"
    
    # Test project queries
    entries = storage.get_entries_by_project("test-project")
    assert len(entries) == 1
    
    # Test deletion
    assert storage.delete_entry(entry_id), "Failed to delete entry"
    assert storage.get_entry(entry_id) is None, "Entry was not deleted"

@pytest.mark.integration
def test_memory_manager_comprehensive(temp_project_dir, test_data):
    """Comprehensive test of memory manager functionality"""

    
    # Now initialize the manager with explicit configuration
    manager = MemoryManager(
        project_root=temp_project_dir,
        project_id="test-project",
        embedding_config=EmbeddingConfig(provider="sentence_transformer", model_name="all-MiniLM-L6-v2"),
        vector_store_config = {
            'qdrant': {
                'collection': 'test_collection',
                'url': None,
                'api_key': None
            }
        }
    )
    
    # Test saving memory with full metadata
    entry_id = manager.save_memory(
        question=test_data["question"],
        answer=test_data["answer"],
        key_findings=test_data["key_findings"],
        files_accessed=test_data["files_accessed"]
    )
    assert entry_id is not None, "Failed to save memory"
    
    # Add a similar question
    similar_question = "What is the authentication mechanism in this project?"
    similar_answer = "This project uses JWT tokens for authentication with role-based access control."
    similar_id = manager.save_memory(
        question=similar_question,
        answer=similar_answer
    )
    
    # Test similarity search
    similar_memories = manager.find_similar_memories(
        query="How does authentication work?",
        limit=2
    )
    assert len(similar_memories) > 0, "Failed to find similar memories"
    
    # Verify memory retrieval
    retrieved_entry = manager.sqlite_storage.get_entry(entry_id)
    assert retrieved_entry is not None
    assert retrieved_entry.question == test_data["question"]
    
    # Test context generation
    context = manager.get_relevant_context(
        query="Authentication system",
        limit=2
    )
    assert context != "", "Failed to generate context"
    
    # Test memory summary
    summary = manager.generate_memory_summary()
    assert "test-project" in summary
    assert "entries" in summary.lower()

def test_delete_memory(memory_manager):
    """Test deleting a specific memory entry"""
    # Save a test memory
    entry_id = memory_manager.save_memory(
        question="Test question for deletion",
        answer="Test answer for deletion",
        key_findings=["Finding 1", "Finding 2"]
    )
    
    # Verify the memory was saved
    entry = memory_manager.get_memory_by_id(entry_id)
    assert entry is not None, "Memory was not saved properly"
    
    # Delete the memory
    result = memory_manager.delete_memory(entry_id)
    assert result is True, "Memory deletion failed"
    
    # Verify the memory was deleted
    entry = memory_manager.get_memory_by_id(entry_id)
    assert entry is None, "Memory was not deleted properly"

def test_clear_project_memories(memory_manager):
    """Test clearing all memories for a project"""
    # Save multiple memories of different types
    memory_manager.save_memory(
        question="Conversation question 1",
        answer="Conversation answer 1",
        entry_type="conversation"
    )
    
    memory_manager.save_memory(
        question="File summary question",
        answer="File summary answer",
        entry_type="file_summary"
    )
    
    memory_manager.save_memory(
        question="Conversation question 2",
        answer="Conversation answer 2",
        entry_type="conversation"
    )
    
    # Verify memories were saved
    all_memories = memory_manager.get_recent_memories(limit=10)
    assert len(all_memories) == 3, "Not all memories were saved"
    
    # Clear only conversation memories
    result = memory_manager.clear_project_memories(entry_type="conversation")
    assert result is True, "Failed to clear conversation memories"
    
    # Verify only conversation memories were cleared
    remaining_memories = memory_manager.get_recent_memories(limit=10)
    assert len(remaining_memories) == 1, "Incorrect number of memories after partial clear"
    assert remaining_memories[0]["entry_type"] == "file_summary", "Wrong memory type remained"
    
    # Clear all remaining memories
    result = memory_manager.clear_project_memories()
    assert result is True, "Failed to clear all memories"
    
    # Verify all memories were cleared
    final_memories = memory_manager.get_recent_memories(limit=10)
    assert len(final_memories) == 0, "Not all memories were cleared"

def test_get_recent_memories(memory_manager):
    """Test retrieving recent memories"""
    # Save memories with timestamps in the past
    for i in range(5):
        memory_manager.save_memory(
            question=f"Question {i}",
            answer=f"Answer {i}",
            entry_type="conversation" if i % 2 == 0 else "file_summary"
        )
        # Add a small delay to ensure different timestamps
        time.sleep(0.1)
    
    # Test retrieving all recent memories
    all_recent = memory_manager.get_recent_memories(limit=10)
    assert len(all_recent) == 5, "Failed to retrieve all recent memories"
    
    # Test retrieving limited number of memories
    limited_recent = memory_manager.get_recent_memories(limit=3)
    assert len(limited_recent) == 3, "Failed to limit recent memories"
    
    # Test retrieving memories by type
    conversation_memories = memory_manager.get_recent_memories(entry_type="conversation")
    assert len(conversation_memories) == 3, "Failed to filter memories by type"
    for memory in conversation_memories:
        assert memory["entry_type"] == "conversation", "Wrong memory type retrieved"

if __name__ == "__main__":
    pytest.main([__file__]) 