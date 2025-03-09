import unittest
import os
import numpy as np

from embedding.embedding_factory import create_embedding_service
from .embedding_service_gemini import GeminiEmbeddingService
from .embedding_config import EmbeddingConfig

@unittest.skipIf(not os.environ.get("GCP_PROJECT_ID"), "No GCP credentials available")
class TestGeminiEmbeddingService(unittest.TestCase):
    """Tests for the Gemini embedding service"""
    
    def setUp(self):
        """Set up test environment"""
        # Initialize service directly without using EmbeddingConfig
        self.service = GeminiEmbeddingService(
            model_name="text-embedding-005",
            dimensionality=768,
            task="RETRIEVAL_DOCUMENT",
            project_id=os.environ.get("GCP_PROJECT_ID"),
            location=os.environ.get("GCP_LOCATION", "us-central1")
        )
        if not self.service.available:
            self.skipTest("Gemini service not available")
    
    def test_initialization(self):
        """Test service initialization"""
        self.assertTrue(self.service.available)
        self.assertEqual(self.service.embedding_dimension, 768)
        self.assertEqual(self.service.model_name, "text-embedding-005")
    
    def test_get_embedding(self):
        """Test getting single embedding"""
        embedding = self.service.get_embedding("test text")
        self.assertEqual(len(embedding), 768)
        self.assertNotEqual(embedding, [0.0] * 768)  # Should not return zero vector
    
    def test_get_batch_embeddings(self):
        """Test getting batch embeddings"""
        texts = ["text1", "text2"]
        embeddings = self.service.get_batch_embeddings(texts)
        
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(len(embeddings[0]), 768)
        self.assertNotEqual(embeddings[0], embeddings[1])  # Different texts should have different embeddings
    
    def test_error_handling(self):
        """Test error handling with invalid input"""
        # Test with None
        embedding = self.service.get_embedding(None)
        self.assertEqual(embedding, [0.0] * 768)
        
        # Test with empty string
        embeddings = self.service.get_batch_embeddings([""])
        self.assertEqual(embeddings, [[0.0] * 768])

    def test_create_gemini_embedding_service(self):
        """Test creating Gemini embedding service"""
        config = EmbeddingConfig(
            model_name="text-embedding-005",
            provider="gemini",
            dimensionality=768,
            task="RETRIEVAL_DOCUMENT",
            project_id=os.environ.get("GCP_PROJECT_ID", "test-project"),
            location=os.environ.get("GCP_LOCATION", "us-central1")
        )
        service = create_embedding_service(config=config)
        self.assertIsInstance(service, GeminiEmbeddingService)

if __name__ == '__main__':
    unittest.main() 