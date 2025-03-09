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




