# langfuse_setup.py

import os
from typing import Optional, Callable

def get_observe():
    if os.getenv("LANGFUSE_HOST"):
        print("using real langfuse decorators")
        from langfuse.decorators import observe
        return observe
    else:
        print("using fake langfuse decorators")
        def fake_observe(as_type: Optional[str] = None, name: Optional[str] = None, capture_input: bool = False, capture_output: bool = False) -> Callable:
            def decorator(func):
                return func
            return decorator
        return fake_observe

def get_langfuse_context():
    if os.getenv("LANGFUSE_HOST"):
        print("using real langfuse context")
        from langfuse.decorators import langfuse_context
        langfuse_context.configure(debug=False)
        return langfuse_context
    else:
        print("using fake langfuse context")
        class FakeLangfuseContext:
            @staticmethod
            def update_current_observation(input: Optional[str], model: Optional[str], output: Optional[str], usage: Optional[dict]):
                pass
            @staticmethod
            def flush():
                pass
        return FakeLangfuseContext()

def initialize_langfuse():
    global observe, langfuse_context
    observe = get_observe()
    langfuse_context = get_langfuse_context()
    return observe, langfuse_context