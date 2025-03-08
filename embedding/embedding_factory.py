import os
import logging
from typing import Optional, Dict, Any, Union
from .embedding_service import OpenAiEmbeddingService
from .embedding_service_sentence_transformer import SentenceTransformerEmbeddingService
from .embedding_service_gemini import GeminiEmbeddingService
from .embedding_config import EmbeddingConfig

logger = logging.getLogger(__name__)

def create_embedding_service(config: EmbeddingConfig) -> Optional[Any]:
    """
    Create an embedding service based on configuration
    
    Args:
        config: Configuration for the embedding service (dict or EmbeddingConfig)
            If None, default configuration will be used
        
    Returns:
        An instance of the appropriate embedding service, or None if no service is available
    """
    
    # Try to create the specified provider
    if config.provider == "openai":
        return _create_openai_service(config)
    elif config.provider == "gemini":
        return _create_gemini_service(config)
    elif config.provider == "sentence_transformer":
        return _create_sentence_transformer(config)
    else:
        logger.warning(f"Unknown embedding provider: {config.provider}, falling back to sentence_transformer")
        config.provider = "sentence_transformer"
        return _create_sentence_transformer(config)

def _create_openai_service(config: EmbeddingConfig) -> Optional[Any]:
    """Attempt to create OpenAI embedding service"""
    try:
        service = OpenAiEmbeddingService(
            model_name=config.model_name
        )
        logger.info("Successfully initialized OpenAI embedding service")
        return service
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI embedding service: {str(e)}")
        return _create_sentence_transformer(config) if config.use_backup else None

def _create_gemini_service(config: EmbeddingConfig) -> Optional[Any]:
    """Attempt to create Gemini embedding service"""
    try:
        service = GeminiEmbeddingService(
            model_name=config.model_name,
            dimensionality=config.dimensionality,
            task=config.task
        )
        if service.available:
            logger.info("Successfully initialized Gemini embedding service")
            return service
        raise Exception("Gemini service initialization failed")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini embedding service: {str(e)}")
        return _create_sentence_transformer(config) if config.use_backup else None

def _create_sentence_transformer(config: EmbeddingConfig) -> Optional[Any]:
    """Create SentenceTransformer embedding service"""
    try:
        service = SentenceTransformerEmbeddingService(
            model_name=config.model_name
        )
        if service.available:
            logger.info("Successfully initialized SentenceTransformer embedding service")
            return service
        raise Exception("SentenceTransformer initialization failed")
    except Exception as e:
        logger.error(f"Failed to initialize SentenceTransformer: {str(e)}")
        return None 