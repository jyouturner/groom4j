import unittest
import numpy as np
import os

from embedding.embedding_factory import create_embedding_service
from .embedding_service import BaseEmbeddingService
from .embedding_service_openai import OpenAiEmbeddingService
from .embedding_service_sentence_transformer import SentenceTransformerEmbeddingService
from .embedding_config import EmbeddingConfig

class TestBaseEmbeddingService(unittest.TestCase):
    """Test the base embedding service interface"""
    
    def setUp(self):
        self.service = BaseEmbeddingService()
    
    def test_initialization(self):
        """Test base service initialization"""
        self.assertFalse(self.service.available)
        self.assertIsNone(self.service.embedding_dimension)
    
    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.service.get_embedding("test")
        
        with self.assertRaises(NotImplementedError):
            self.service.get_batch_embeddings(["test1", "test2"])
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]  # Same as vec1
        
        # Orthogonal vectors should have similarity 0
        self.assertAlmostEqual(self.service.cosine_similarity(vec1, vec2), 0.0)
        
        # Same vectors should have similarity 1
        self.assertAlmostEqual(self.service.cosine_similarity(vec1, vec3), 1.0)
        
        # Test with zero vector
        zero_vec = [0.0, 0.0, 0.0]
        self.assertEqual(self.service.cosine_similarity(vec1, zero_vec), 0.0)

@unittest.skipIf('OPENAI_API_KEY' not in os.environ, "OpenAI API key not found")
class TestOpenAIEmbeddingService(unittest.TestCase):
    """Test the OpenAI embedding service"""
    
    def setUp(self):
        # Initialize service
        self.service = OpenAiEmbeddingService(api_key=os.environ['OPENAI_API_KEY'], model_name="text-embedding-3-small")
    
    def tearDown(self):
        """Clean up mocks"""
        pass
    
    def test_initialization(self):
        """Test service initialization"""
        self.assertTrue(self.service.available)
        self.assertEqual(self.service.embedding_dimension, 1536)
        self.assertEqual(self.service.model_name, "text-embedding-3-small")
    
    def test_initialization_no_api_key(self):
        """Test initialization without API key"""
        del os.environ['OPENAI_API_KEY']
        service = OpenAiEmbeddingService(api_key="", model_name="text-embedding-3-small")
        self.assertFalse(service.available)
    
    def test_get_embedding(self):
        """Test getting single embedding"""
        embedding = self.service.get_embedding("test text")
        
        self.assertEqual(len(embedding), 1536)
       
    
    def test_get_batch_embeddings(self):
        """Test getting batch embeddings"""
        texts = ["text1", "text2"]
    
        embeddings = self.service.get_batch_embeddings(texts)
        
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(len(embeddings[0]), 1536)
        
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        import time
        
        # Record start time
        start_time = time.time()
        
        # Make multiple requests
        for _ in range(3):
            self.service.get_embedding("test")
        
        # Check that appropriate time has passed
        elapsed = time.time() - start_time
        min_expected_time = (2 * 60.0 / self.service.requests_per_minute)  # Time for 2 waits
        
        self.assertGreaterEqual(elapsed, min_expected_time)
    
    


class TestEmbeddingFactory(unittest.TestCase):
    """Test the embedding service factory"""
    
    def setUp(self):        
        # Create test config
        self.test_config = EmbeddingConfig(
            model_name="all-MiniLM-L6-v2",
            provider="sentence_transformer"
        )
    
    def test_create_embedding_service(self):
        """Test creating embedding service"""
        service = create_embedding_service(config=self.test_config)
        self.assertIsInstance(service, BaseEmbeddingService)
    

if __name__ == '__main__':
    unittest.main() 