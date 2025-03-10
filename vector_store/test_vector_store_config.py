import os
import pytest
from pathlib import Path
import yaml
from .vector_store_config import (
    load_vector_store_config,
    get_vector_store_defaults,
    update_application_yaml_with_vector_store_defaults
)

@pytest.fixture
def temp_config_file(tmp_path):
    """Fixture to create a temporary config file for testing"""
    config_path = tmp_path / "test_application.yml"
    test_config = {
        'vector_store': {
            'use': 'qdrant',
            'embedding_provider': 'openai',
            'qdrant': {
                'api_key': 'test_api_key',
                'url': 'http://test.url',
                'collection': 'test_collection'
            }
        }
    }
    with open(config_path, 'w') as f:
        yaml.dump(test_config, f)
    return config_path

@pytest.fixture
def clean_env():
    """Fixture to clean environment variables before each test"""
    # Save original environment variables
    original_env = {
        'VECTOR_STORE_USE': os.environ.get('VECTOR_STORE_USE'),
        'EMBEDDING_PROVIDER': os.environ.get('EMBEDDING_PROVIDER'),
        'QDRANT_API_KEY': os.environ.get('QDRANT_API_KEY'),
        'QDRANT_URL': os.environ.get('QDRANT_URL'),
        'QDRANT_COLLECTION': os.environ.get('QDRANT_COLLECTION')
    }
    
    # Clear relevant environment variables
    for key in original_env.keys():
        if key in os.environ:
            del os.environ[key]
    
    yield
    
    # Restore original environment variables
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]

def test_load_vector_store_config_with_valid_file(temp_config_file, clean_env):
    config = load_vector_store_config(temp_config_file)
    
    assert config['use'] == 'qdrant'
    assert config['embedding_provider'] == 'openai'
    assert config['qdrant']['api_key'] == 'test_api_key'
    assert config['qdrant']['url'] == 'http://test.url'
    assert config['qdrant']['collection'] == 'test_collection'
    
    # Check if environment variables were set
    assert os.environ['VECTOR_STORE_USE'] == 'qdrant'
    assert os.environ['EMBEDDING_PROVIDER'] == 'openai'
    assert os.environ['QDRANT_API_KEY'] == 'test_api_key'
    assert os.environ['QDRANT_URL'] == 'http://test.url'
    assert os.environ['QDRANT_COLLECTION'] == 'test_collection'

def test_load_vector_store_config_with_nonexistent_file(clean_env):
    config = load_vector_store_config('nonexistent.yml')
    assert config == {}

def test_load_vector_store_config_with_invalid_yaml(tmp_path, clean_env):
    invalid_config_path = tmp_path / "invalid.yml"
    with open(invalid_config_path, 'w') as f:
        f.write("invalid: yaml: content:")
    
    config = load_vector_store_config(invalid_config_path)
    assert config == {}

def test_get_vector_store_defaults(clean_env):
    # Set some environment variables
    os.environ['VECTOR_STORE_USE'] = 'test_store'
    os.environ['EMBEDDING_PROVIDER'] = 'test_provider'
    os.environ['QDRANT_COLLECTION'] = 'test_collection'
    
    defaults = get_vector_store_defaults()
    
    assert defaults['use'] == 'test_store'
    assert defaults['embedding_provider'] == 'test_provider'
    assert defaults['qdrant']['collection'] == 'test_collection'
    assert defaults['qdrant']['url'] == ''
    assert defaults['qdrant']['api_key'] == ''

def test_update_application_yaml_with_vector_store_defaults(tmp_path, clean_env):
    config_path = tmp_path / "new_config.yml"
    
    # Test creating new file
    update_application_yaml_with_vector_store_defaults(config_path)
    assert config_path.exists()
    
    # Verify content
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    assert 'vector_store' in config
    assert config['vector_store']['use'] == 'qdrant'
    assert config['vector_store']['embedding_provider'] == 'auto'

def test_update_existing_config_without_vector_store(tmp_path, clean_env):
    config_path = tmp_path / "existing_config.yml"
    
    # Create existing config without vector_store section
    initial_config = {'other_section': 'some_value'}
    with open(config_path, 'w') as f:
        yaml.dump(initial_config, f)
    
    update_application_yaml_with_vector_store_defaults(config_path)
    
    # Verify content
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    assert 'other_section' in config
    assert 'vector_store' in config
    assert config['vector_store']['use'] == 'qdrant'
    assert config['other_section'] == 'some_value' 