# langfuse_setup.py
import os
from typing import Optional, Callable

if os.getenv("LANGFUSE_HOST"):
    from langfuse.decorators import observe, langfuse_context
    langfuse_context.configure(debug=False)
else:
    # fake the langfuse decorators to avoid import errors
    def observe(as_type: Optional[str] = None, capture_input: bool = False, capture_output: bool = False) -> Callable:
        def decorator(func):
            return func
        return decorator

    class langfuse_context:
        @staticmethod
        def update_current_observation(input: Optional[str], model: Optional[str], output: Optional[str], usage: Optional[dict]):
            pass