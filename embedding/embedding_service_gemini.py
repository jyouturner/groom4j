import os
import time
from typing import List
import logging
import numpy as np

logger = logging.getLogger(__name__)

class GeminiEmbeddingService:
    """Embedding service using Google's Gemini models"""
    
    def __init__(self, project_id: str, location: str, model_name: str = "text-embedding-005", dimensionality: int = 768, task: str = "RETRIEVAL_DOCUMENT"):
        """Initialize with Google Gemini model"""
        try:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
            
            if not project_id:
                raise ValueError("GCP_PROJECT_ID environment variable not set")
            
            # Initialize Google Cloud
            aiplatform.init(
                project=project_id,
                location=location,
            )
            
            self.model_name = model_name
            self.model = TextEmbeddingModel.from_pretrained(model_name)
            self.embedding_dimension = dimensionality
            self.task = task
            self.available = True
            self.requests_per_minute = 100  # Adjust based on your quota
            self.last_request_time = 0
            
            logger.info(f"Initialized GeminiEmbeddingService with model {model_name}")
        except ImportError as e:
            logger.error("Google Cloud AI Platform not available. Install with 'pip install google-cloud-aiplatform vertexai'")
            self.available = False
            self.embedding_dimension = 768  # Default fallback dimension
        except Exception as e:
            logger.error(f"Error initializing Gemini embedding service: {str(e)}")
            self.available = False
            self.embedding_dimension = 768  # Default fallback dimension
    
    def _enforce_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for input text"""
        if not self.available:
            # Return zero vector as fallback
            return [0.0] * self.embedding_dimension
            
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Truncate text if needed (model has its own limits, but let's be safe)
            if len(text) > 10000:
                text = text[:10000]
            
            # Create TextEmbeddingInput with the specified task
            from vertexai.language_models import TextEmbeddingInput
            embedding_input = TextEmbeddingInput(text, self.task)
            
            # Generate embedding
            embedding_response = self.model.get_embeddings(
                [embedding_input], 
                output_dimensionality=self.embedding_dimension
            )
            
            # Extract the embedding vector
            if embedding_response and embedding_response[0].values:
                embedding = embedding_response[0].values
                return embedding
            
            print("Empty embedding response from Gemini")
            return [0.0] * self.embedding_dimension
        except Exception as e:
            print(f"Error generating Gemini embedding: {str(e)}")
            return [0.0] * self.embedding_dimension
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        if not self.available:
            # Return zero vectors as fallback
            return [[0.0] * self.embedding_dimension for _ in range(len(texts))]
            
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Process each text
            processed_texts = [text[:10000] if len(text) > 10000 else text for text in texts]
            
            # Create TextEmbeddingInput objects with the specified task
            from vertexai.language_models import TextEmbeddingInput
            embedding_inputs = [TextEmbeddingInput(text, self.task) for text in processed_texts]
            
            # Generate embeddings in batch
            embedding_responses = self.model.get_embeddings(
                embedding_inputs,
                output_dimensionality=self.embedding_dimension
            )
            
            # Extract embedding vectors
            if embedding_responses:
                embeddings = [emb.values for emb in embedding_responses]
                return embeddings
            
            print("Empty batch embedding response from Gemini")
            return [[0.0] * self.embedding_dimension for _ in range(len(texts))]
        except Exception as e:
            print(f"Error generating batch Gemini embeddings: {str(e)}")
            return [[0.0] * self.embedding_dimension for _ in range(len(texts))]
    
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