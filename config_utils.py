import os
import yaml
from pathlib import Path

def load_config_to_env(config_path=None):
    if config_path is None:
        config_path = Path('application.yml')
    else:
        config_path = Path(config_path)
    print(f"Loading configuration from {config_path.absolute()}")
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path.absolute()}")
    
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    
    def flatten_dict(d, parent_key='', sep='_'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key.upper(), str(v)))
        return dict(items)
    
    flattened_config = flatten_dict(config)
    os.environ.update(flattened_config)

# You can add other config-related utility functions here if needed