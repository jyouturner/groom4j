import unittest
import os
from .embedding_service_gemini import GeminiEmbeddingService

class TestGeminiEmbeddingServiceIntegration(unittest.TestCase):
    """Integration tests for Gemini embedding service using real GCP"""
    
    @classmethod
    def setUpClass(cls):
        """Set up the embedding service once for all tests"""
        # Skip all tests if GCP_PROJECT_ID is not set
        if not os.environ.get("GCP_PROJECT_ID"):
            raise unittest.SkipTest("GCP_PROJECT_ID environment variable not set")
            
        cls.service = GeminiEmbeddingService(
            model_name="text-embedding-005",
            dimensionality=768,
            task="RETRIEVAL_DOCUMENT",
            project_id=os.environ.get("GCP_PROJECT_ID"),
            location=os.environ.get("GCP_LOCATION", "us-central1")
        )
        if not cls.service.available:
            raise unittest.SkipTest("Gemini embedding service not available")
    
    def test_real_embedding(self):
        """Test getting a real embedding from Gemini"""
        text = "This is a test of the Gemini embedding service."
        embedding = self.service.get_embedding(text)
        
        self.assertEqual(len(embedding), 768)
        # Check that we don't get a zero vector
        self.assertNotEqual(embedding, [0.0] * 768)
    
    def test_real_batch_embeddings(self):
        """Test getting real batch embeddings"""
        texts = [
            "First test text",
            "Second test text",
            "Third test text"
        ]
        embeddings = self.service.get_batch_embeddings(texts)
        
        self.assertEqual(len(embeddings), 3)
        self.assertEqual(len(embeddings[0]), 768)
        # Check that embeddings are different
        self.assertNotEqual(embeddings[0], embeddings[1])
    
    def test_similar_texts(self):
        """Test that similar texts get similar embeddings"""
        text1 = "The cat sat on the mat"
        text2 = "A cat is sitting on a mat"
        text3 = "The weather is sunny today"
        
        emb1 = self.service.get_embedding(text1)
        emb2 = self.service.get_embedding(text2)
        emb3 = self.service.get_embedding(text3)
        
        # Similar texts should have higher similarity
        sim_similar = self.service.cosine_similarity(emb1, emb2)
        sim_different = self.service.cosine_similarity(emb1, emb3)
        
        self.assertGreater(sim_similar, sim_different)
    
    def test_long_text(self):
        """Test embedding of long text"""
        long_text = "This is a very long text. " * 1000
        embedding = self.service.get_embedding(long_text)
        
        self.assertEqual(len(embedding), 768)
        self.assertNotEqual(embedding, [0.0] * 768)

if __name__ == '__main__':
    unittest.main() 