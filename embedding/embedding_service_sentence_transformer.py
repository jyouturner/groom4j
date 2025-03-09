from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from .embedding_service import BaseEmbeddingService

class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Implementation of embedding service using SentenceTransformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the SentenceTransformer embedding service
        
        Args:
            model_name: Name of the sentence-transformer model to use
                       Default is "all-MiniLM-L6-v2" which is a good balance
                       of speed and performance
        """
        super().__init__()
        try:
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            self.available = True
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"Failed to initialize SentenceTransformer model: {e}")
            self.available = False
            self.embedding_dimension = None
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for input text
        
        Args:
            text: The input text to embed
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            RuntimeError: If the embedding service is not available
        """
        if not self.available:
            raise RuntimeError("SentenceTransformer embedding service is not available")
        
        # Generate embedding
        embedding = self.model.encode(text)
        
        # Convert numpy array to list of floats
        return embedding.tolist()
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts to embed
        
        Returns:
            List of embedding vectors (each a list of floats)
        
        Raises:
            RuntimeError: If the embedding service is not available
        """
        if not self.available:
            raise RuntimeError("SentenceTransformer embedding service is not available")
        
        # Generate embeddings in batch mode (more efficient)
        embeddings = self.model.encode(texts)
        
        # Convert numpy arrays to lists of floats
        return embeddings.tolist()
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model
        
        Returns:
            Dictionary with model information
        """
        if not self.available:
            return {"available": False}
        
        return {
            "available": self.available,
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension
        }