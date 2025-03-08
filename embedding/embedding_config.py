from dataclasses import dataclass, fields
from typing import Optional

@dataclass
class EmbeddingConfig:
    """Configuration for embedding services"""
    # Common configuration
    model_name: str
    provider: str = "sentence_transformer"
    use_backup: bool = True
    
    # OpenAI specific
    api_key: Optional[str] = None
    
    # Gemini specific
    dimensionality: int = 768
    task: str = "RETRIEVAL_DOCUMENT"
    project_id: Optional[str] = None
    location: str = "us-central1"
    
    # SentenceTransformer specific
    # Uses model_name from common config
    
    @classmethod
    def default_config(cls) -> 'EmbeddingConfig':
        """Create default configuration"""
        return cls(
            model_name="all-MiniLM-L6-v2",
            provider="sentence_transformer"
        )
    
    @classmethod
    def from_dict(cls, config: dict) -> 'EmbeddingConfig':
        """Create configuration from dictionary"""
        # Filter out None values and unknown fields
        valid_fields = {f.name for f in fields(cls)}
        filtered_config = {k: v for k, v in config.items() if k in valid_fields and v is not None}
        return cls(**filtered_config) 