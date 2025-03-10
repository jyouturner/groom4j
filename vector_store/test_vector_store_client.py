import pytest
import numpy as np
from .vector_store_client import QdrantVectorStore
import time
import os

# Register the integration mark
def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )

@pytest.fixture
def vector_store(request):
    """Create a test vector store instance"""
    # Determine if we're running integration tests
    is_integration = request.config.getoption("-m") == "integration"
    
    store = QdrantVectorStore(
        collection_name="test_collection",
        vector_size=4,  # Using small vectors for testing
        skip_payload_indexes=not is_integration  # Skip indexes for local tests
    )
    store.initialize_collection()
    return store

def test_store_and_retrieve_embedding(vector_store):
    """Test storing and retrieving a single embedding"""
    # Test data
    vector = [1.0, 0.0, 0.0, 0.0]
    text = "Test document"
    metadata = {
        "project_id": "test_project",
        "entry_type": "test",
        "timestamp": int(time.time())
    }
    
    # Store embedding
    entry_id = vector_store.store_embedding(
        vector=vector,
        text=text,
        metadata=metadata
    )
    
    assert entry_id is not None
    
    # Retrieve by ID
    result = vector_store.get_by_id(entry_id)
    
    assert result is not None
    assert result["text"] == text
    assert result["project_id"] == metadata["project_id"]
    assert result["entry_type"] == metadata["entry_type"]

def test_search_similar(vector_store):
    """Test searching for similar vectors"""
    # Store multiple test vectors
    vectors = [
        ([1.0, 0.0, 0.0, 0.0], "Document 1"),
        ([0.9, 0.1, 0.0, 0.0], "Document 2"),
        ([0.0, 1.0, 0.0, 0.0], "Document 3"),
    ]
    
    for i, (vector, text) in enumerate(vectors):
        vector_store.store_embedding(
            vector=vector,
            text=text,
            metadata={
                "project_id": "test_project",
                "entry_type": "test",
                "timestamp": int(time.time())
            }
        )
    
    # Search with a query vector similar to first two documents
    results = vector_store.search_similar(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        project_id="test_project",
        entry_type="test",
        limit=2
    )
    
    assert len(results) == 2
    assert results[0]["text"] in ["Document 1", "Document 2"]
    assert results[1]["text"] in ["Document 1", "Document 2"]
    assert results[0]["score"] > results[1]["score"]  # First result should have higher score

def test_delete_operations(vector_store):
    """Test deletion operations"""
    # Store test vector
    vector = [1.0, 0.0, 0.0, 0.0]
    text = "Test document"
    metadata = {
        "project_id": "test_project",
        "entry_type": "test",
        "timestamp": int(time.time())
    }
    
    entry_id = vector_store.store_embedding(
        vector=vector,
        text=text,
        metadata=metadata
    )
    
    # Verify storage
    assert vector_store.get_by_id(entry_id) is not None
    
    # Test delete by ID
    assert vector_store.delete_by_id(entry_id) is True
    assert vector_store.get_by_id(entry_id) is None
    
    # Test delete by filter
    new_entry_id = vector_store.store_embedding(
        vector=vector,
        text=text,
        metadata=metadata
    )
    
    assert vector_store.delete_by_filter(
        project_id="test_project",
        entry_type="test"
    ) is True
    
    assert vector_store.get_by_id(new_entry_id) is None

def test_filter_conditions(vector_store):
    """Test searching with different filter conditions"""
    # Store vectors with different metadata
    vectors = [
        ([1.0, 0.0, 0.0, 0.0], "Project 1 Doc", "project_1"),
        ([0.9, 0.1, 0.0, 0.0], "Project 2 Doc", "project_2"),
    ]
    
    for vector, text, project_id in vectors:
        vector_store.store_embedding(
            vector=vector,
            text=text,
            metadata={
                "project_id": project_id,
                "entry_type": "test",
                "timestamp": int(time.time())
            }
        )
    
    # Search with project filter
    results = vector_store.search_similar(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        project_id="project_1"
    )
    
    assert len(results) == 1
    assert results[0]["text"] == "Project 1 Doc"
    assert results[0]["project_id"] == "project_1"

@pytest.fixture
def cloud_vector_store():
    """Create a test vector store instance using cloud Qdrant if credentials are available"""
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    
    if not url or not api_key:
        pytest.skip("Qdrant cloud credentials not available")
        
    store = QdrantVectorStore(
        collection_name="test_collection_cloud",
        vector_size=4,
        url=url
    )
    store.initialize_collection()
    yield store
    
    # Cleanup: delete the test collection after tests
    try:
        store.delete_by_filter(project_id="test_project")
    except Exception as e:
        print(f"Cleanup failed: {e}")

@pytest.mark.integration
class TestCloudQdrantIntegration:
    """Integration tests using cloud Qdrant instance"""
    
    def test_cloud_store_and_retrieve(self, cloud_vector_store):
        """Test storing and retrieving with cloud instance"""
        vector = [1.0, 0.0, 0.0, 0.0]
        text = "Cloud test document"
        metadata = {
            "project_id": "test_project",
            "entry_type": "cloud_test",
            "timestamp": int(time.time())
        }
        
        entry_id = cloud_vector_store.store_embedding(
            vector=vector,
            text=text,
            metadata=metadata
        )
        
        assert entry_id is not None
        
        # Verify retrieval
        result = cloud_vector_store.get_by_id(entry_id)
        assert result is not None
        assert result["text"] == text
        assert result["project_id"] == metadata["project_id"]
    
    def test_cloud_search_performance(self, cloud_vector_store):
        """Test search performance with cloud instance"""
        # Store 100 test vectors
        vectors = []
        for i in range(100):
            # Create slightly different vectors
            vector = [0.9 + (i * 0.001), 0.1, 0.0, 0.0]
            vectors.append((vector, f"Document {i}"))
        
        # Batch store vectors
        for vector, text in vectors:
            cloud_vector_store.store_embedding(
                vector=vector,
                text=text,
                metadata={
                    "project_id": "test_project",
                    "entry_type": "perf_test",
                    "timestamp": int(time.time())
                }
            )
        
        # Measure search time
        start_time = time.time()
        results = cloud_vector_store.search_similar(
            query_vector=[1.0, 0.0, 0.0, 0.0],
            project_id="test_project",
            entry_type="perf_test",
            limit=10
        )
        search_time = time.time() - start_time
        
        assert len(results) == 10
        assert search_time < 1.0  # Search should complete within 1 second
        
        # Verify results are ordered by similarity
        scores = [r["score"] for r in results]
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    def test_cloud_concurrent_operations(self, cloud_vector_store):
        """Test concurrent operations on cloud instance"""
        import concurrent.futures
        
        def store_and_retrieve():
            vector = [1.0, 0.0, 0.0, 0.0]
            text = f"Concurrent test {time.time()}"
            metadata = {
                "project_id": "test_project",
                "entry_type": "concurrent_test",
                "timestamp": int(time.time())
            }
            
            entry_id = cloud_vector_store.store_embedding(
                vector=vector,
                text=text,
                metadata=metadata
            )
            
            # Immediately try to retrieve it
            result = cloud_vector_store.get_by_id(entry_id)
            return result is not None
        
        # Run 10 concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(store_and_retrieve) for _ in range(10)]
            results = [f.result() for f in futures]
        
        assert all(results)  # All operations should succeed 