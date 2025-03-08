import os
import time
from typing import List, Dict, Any, Optional, Union
import numpy as np
from openai import OpenAI
import tiktoken
import logging

logger = logging.getLogger(__name__)

class BaseEmbeddingService:
    """Base class for embedding services defining the interface"""
    
    def __init__(self):
        self.available = False
        self.embedding_dimension = None
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for input text"""
        raise NotImplementedError
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        raise NotImplementedError
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        # Convert to numpy arrays for easier calculation
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
            
        similarity = dot_product / (norm_v1 * norm_v2)
        
        # Ensure the result is within [-1, 1]
        return max(min(similarity, 1.0), -1.0)

class OpenAiEmbeddingService(BaseEmbeddingService):
    """OpenAI-based embedding service"""
    
    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        """Initialize embedding service with model details"""
        super().__init__()
        self.model_name = model_name
        
            
        try:
            self.client = OpenAI(api_key=api_key)
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.max_tokens = 8191  # Max tokens for text-embedding-3-small model
            self.embedding_dimension = 1536  # Dimension for text-embedding-3-small
            
            # Rate limiting settings
            self.requests_per_minute = 10
            self.last_request_time = 0
            
            self.available = True
            logger.info(f"Initialized OpenAI EmbeddingService with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embedding service: {str(e)}")
    
    def _enforce_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within token limits"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= self.max_tokens:
            return text
            
        # Truncate to max tokens and decode back to text
        truncated_tokens = tokens[:self.max_tokens]
        return self.encoding.decode(truncated_tokens)
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for input text"""
        if not self.available:
            logger.warning("OpenAI embedding service not available")
            return [0.0] * self.embedding_dimension
            
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Truncate text if needed
            processed_text = self._truncate_text(text)
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model_name,
                input=processed_text
            )
            
            # Extract and return the embedding vector
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return [0.0] * self.embedding_dimension
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        if not self.available:
            logger.warning("OpenAI embedding service not available")
            return [[0.0] * self.embedding_dimension for _ in range(len(texts))]
            
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Process each text
            processed_texts = [self._truncate_text(text) for text in texts]
            
            # Generate embeddings in batch
            response = self.client.embeddings.create(
                model=self.model_name,
                input=processed_texts
            )
            
            # Extract and return embedding vectors
            embeddings = [data.embedding for data in response.data]
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return [[0.0] * self.embedding_dimension for _ in range(len(texts))]


