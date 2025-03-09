from openai import OpenAI
import tiktoken
from .embedding_service import BaseEmbeddingService
import logging
from typing import List
import time

logger = logging.getLogger(__name__)

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