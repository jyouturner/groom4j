import os
from typing import Optional
from projectfiles import ProjectFiles
# Remove this import to avoid circular dependency
# from functions import get_static_notes
from llm_client import LLMQueryManager

def count_tokens(text):
    import tiktoken
    encoding = tiktoken.get_encoding("gpt2")
    return len(encoding.encode(text))

# Define a simplified version of get_static_notes here
def get_package_notes(pf):
    """Get package notes from ProjectFiles object"""
    if hasattr(pf, 'get_package_notes'):
        return pf.get_package_notes()
    return ""

def initiate_llm_query_manager(pf: Optional[ProjectFiles], system_prompt, reused_prompt_template, tier="tier1"):
    use_llm = os.environ.get("LLM_USE")
    # Get max_tokens from environment if available
    max_tokens_tier1 = int(os.environ.get("LLM_MAX_TOKENS_TIER1", "4096"))
    max_tokens_tier2 = int(os.environ.get("LLM_MAX_TOKENS_TIER2", "2048"))
    max_tokens = max_tokens_tier1 if tier == "tier1" else max_tokens_tier2
    
    # prompts can be reused and cached in the LLM if it is supported
    if pf is not None:
        # Use our local function instead of importing from functions
        package_notes = get_package_notes(pf)
        project_tree = pf.to_tree()
        file_notes = pf.get_file_notes()
        # check the token size limit
        tokenSize = count_tokens(package_notes)
        if tokenSize > 200000:
            #raise ValueError("The system_prompt exceeds the maximum token limit")
            # reduce the size of package notes
            package_notes = package_notes[:120000]
    else:
        project_tree = ""
        package_notes = ""
        file_notes = ""
    if reused_prompt_template is not None:
        cached_prompt = reused_prompt_template.format(project_tree=project_tree, 
        package_notes=package_notes, file_notes=file_notes)
    else:
        cached_prompt = None
    #FIXME: need to add the max_calls, period, max_tokens_per_min, max_tokens_per_day, encoding_name to application.yml
    query_manager = LLMQueryManager(use_llm=use_llm, tier=tier, system_prompt=system_prompt, cached_prompt=cached_prompt,
                                    max_tokens=max_tokens,
                                    max_calls=1000,
                                    period=60,
                                    max_tokens_per_min=80000,
                                    max_tokens_per_day=2500000,
                                    encoding_name="cl100k_base")
    
    return query_manager 