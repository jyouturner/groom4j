import os
import yaml
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)

def load_vector_store_config(config_path=None):
    """
    Load vector store configuration from the application.yml file
    and set environment variables
    
    Args:
        config_path: Path to the config file (defaults to application.yml)
        
    Returns:
        dict: The vector store configuration
    """
    # Use the provided config path or default to application.yml
    if config_path is None:
        config_path = Path('application.yml')
    else:
        config_path = Path(config_path)
    
    logger.info(f"Loading vector store configuration from {config_path.absolute()}")
    
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path.absolute()}")
        return {}
    
    try:
        # Load the YAML configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        
        # Extract vector store configuration
        vector_store_config = config.get('vector_store', {})
        
        # Set environment variables based on configuration
        if vector_store_config:
            # Set which vector store to use
            vector_store_use = vector_store_config.get('use', 'qdrant')
            os.environ["VECTOR_STORE_USE"] = vector_store_use
            logger.info(f"Using vector store: {vector_store_use}")
            
            # Set embedding provider
            embedding_provider = vector_store_config.get('embedding_provider', 'auto')
            os.environ["EMBEDDING_PROVIDER"] = embedding_provider
            logger.info(f"Using embedding provider: {embedding_provider}")
            
            # Set Qdrant configuration if present
            if 'qdrant' in vector_store_config:
                qdrant_config = vector_store_config['qdrant']
                
                # Set Qdrant API key
                if 'api_key' in qdrant_config:
                    os.environ["QDRANT_API_KEY"] = qdrant_config['api_key']
                    logger.info("Qdrant API key set")
                
                # Set Qdrant URL if present
                if 'url' in qdrant_config:
                    os.environ["QDRANT_URL"] = qdrant_config['url']
                    logger.info(f"Qdrant URL set to {qdrant_config['url']}")
                    
                # Set Qdrant collection name if present
                if 'collection' in qdrant_config:
                    os.environ["QDRANT_COLLECTION"] = qdrant_config['collection']
                    logger.info(f"Qdrant collection set to {qdrant_config['collection']}")
        
        return vector_store_config
    except Exception as e:
        logger.error(f"Error loading vector store configuration: {str(e)}")
        return {}

def get_vector_store_defaults():
    """
    Get the default configuration for the vector store
    
    Returns:
        dict: Default configuration
    """
    return {
        'use': os.environ.get("VECTOR_STORE_USE", "qdrant"),
        'embedding_provider': os.environ.get("EMBEDDING_PROVIDER", "auto"),
        'qdrant': {
            'collection': os.environ.get("QDRANT_COLLECTION", "java_assistant"),
            'url': os.environ.get("QDRANT_URL", ""),
            'api_key': os.environ.get("QDRANT_API_KEY", "")
        }
    }

def update_application_yaml_with_vector_store_defaults(config_path=None):
    """
    Update application.yml with vector store defaults if not present
    
    Args:
        config_path: Path to the config file (defaults to application.yml)
    """
    # Use the provided config path or default to application.yml
    if config_path is None:
        config_path = Path('application.yml')
    else:
        config_path = Path(config_path)
    
    # If the file doesn't exist, create it
    if not config_path.exists():
        logger.info(f"Creating new configuration file: {config_path.absolute()}")
        with open(config_path, 'w') as config_file:
            yaml.dump({'vector_store': get_vector_store_defaults()}, config_file)
        return
    
    # Load existing configuration
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file) or {}
    
    # Check if vector_store section is already present
    if 'vector_store' not in config:
        logger.info("Adding vector_store section to configuration")
        config['vector_store'] = get_vector_store_defaults()
        
        # Write updated configuration
        with open(config_path, 'w') as config_file:
            yaml.dump(config, config_file)
