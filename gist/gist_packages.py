import os
import sys
import json
import argparse
from .projectfiles import ProjectFiles

# Read the package analysis prompt template
def load_package_analysis_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), 'package-semantic-analysis-prompt.md')
    with open(prompt_path, 'r') as f:
        return f.read()

system_prompt = """
You are a world-class software architect and developer. You are analyzing a Java package structure based on semantic analysis of its files. Your task is to synthesize a comprehensive understanding of each package based on the semantic analysis of its files and subpackages.
"""

def init_query_manager(project_root=None):
    # Import and initialize query manager only when needed
    from config_utils import load_config_to_env
    load_config_to_env()
    from llm_client import LLMQueryManager
    from llm_utils import initiate_llm_query_manager
    #pf = ProjectFiles(repo_root_path=project_root)
    #pf.load_code_files()
    return initiate_llm_query_manager(
        pf=None, 
        system_prompt=system_prompt, 
        reused_prompt_template=None, 
        tier="tier2"
    )

# Lazy initialization of query_manager
_query_manager = None
def get_query_manager(project_root=None):
    global _query_manager
    if _query_manager is None:
        _query_manager = init_query_manager(project_root=project_root)
    #if not hasattr(_query_manager, 'pf') or _query_manager.pf is None:
    #    raise ValueError("ProjectFiles instance not set in query_manager")
    return _query_manager

def real_package_gisting(package, subpackage_notes, filenotes):
    print(f"\n\nAnalyzing package: {package}")
    
    # Use the package analysis prompt template
    prompt_template = load_package_analysis_prompt()
    
    # Create a dictionary of format parameters
    format_params = {
        "package_name": package,
        "subpackage_notes": subpackage_notes,
        "file_notes": filenotes
    }
    
    # Format the prompt using the dictionary
    try:
        prompt = prompt_template.format(**format_params)
    except KeyError as e:
        print(f"Error formatting prompt: {e}")
        raise
    
    # Get JSON response from LLM using lazy-loaded query manager
    json_summary = get_query_manager().query(prompt)
    
    try:
        # Parse the JSON response
        summary_obj = json.loads(json_summary)
        
        # Convert JSON to a formatted string summary for persistence
        summary = (
            f"Package: {summary_obj['package_name']}\n"
            f"Primary Purpose: {summary_obj['primary_purpose']}\n"
            f"Architectural Role: {summary_obj['architectural_role']}\n\n"
        )
        
        # Key Components
        if summary_obj.get('key_components'):
            summary += "Key Components:\n"
            for comp in summary_obj['key_components']:
                summary += f"  - {comp['name']} ({comp['type']})\n"
                summary += f"    {comp['responsibility']}\n"
        
        # Component Relationships
        if summary_obj.get('component_relationships'):
            summary += "\nComponent Relationships:\n"
            for rel in summary_obj['component_relationships']:
                summary += (
                    f"  - {rel['source']} -> {rel['target']} ({rel['relationship_type']})\n"
                    f"    Data: {rel['data_exchanged']}\n"
                    f"    Context: {rel['context']}\n"
                )
        
        # Data Flows
        if summary_obj.get('data_flows'):
            summary += "\nData Flows:\n"
            for flow in summary_obj['data_flows']:
                summary += f"  - {flow['description']}\n"
                summary += f"    Input: {flow['input_type']}\n"
                summary += f"    Output: {flow['output_type']}\n"
                for step in flow['flow_steps']:
                    summary += f"    * {step['component']}: {step['action']}\n"
        
        # Design Patterns
        if summary_obj.get('design_patterns'):
            summary += "\nDesign Patterns:\n"
            for pattern in summary_obj['design_patterns']:
                summary += (
                    f"  - {pattern['pattern']}\n"
                    f"    Implementation: {pattern['implementation']}\n"
                    f"    Components: {', '.join(pattern['components_involved'])}\n"
                )
        
        # Package Boundaries
        if summary_obj.get('package_boundaries'):
            summary += "\nPackage Boundaries:\n"
            if summary_obj['package_boundaries'].get('incoming_interfaces'):
                summary += "  Incoming Interfaces:\n"
                for iface in summary_obj['package_boundaries']['incoming_interfaces']:
                    summary += f"    - {iface['name']}: {iface['purpose']}\n"
                    summary += f"      Consumers: {', '.join(iface['consumers'])}\n"
            
            if summary_obj['package_boundaries'].get('outgoing_dependencies'):
                summary += "  Outgoing Dependencies:\n"
                for dep in summary_obj['package_boundaries']['outgoing_dependencies']:
                    summary += f"    - {dep['target']} ({dep['criticality']})\n"
                    summary += f"      Usage: {dep['usage']}\n"
        
        # Service Orchestration
        if summary_obj.get('service_orchestration'):
            summary += "\nService Orchestration:\n"
            for orch in summary_obj['service_orchestration']:
                summary += f"  - Process: {orch['process_name']}\n"
                summary += f"    Orchestrator: {orch['orchestrator']}\n"
                for step in orch['sequence']:
                    summary += f"    {step['step']}. {step['service']}: {step['purpose']}\n"
        
        # Cross-cutting Concerns
        if summary_obj.get('cross_cutting_concerns'):
            summary += "\nCross-cutting Concerns:\n"
            for concern in summary_obj['cross_cutting_concerns']:
                summary += (
                    f"  - {concern['concern']}\n"
                    f"    Implementation: {concern['implementation']}\n"
                    f"    Affects: {', '.join(concern['components_affected'])}\n"
                )
        
        # Package Structure
        if summary_obj.get('package_structure'):
            summary += (
                f"\nPackage Structure:\n"
                f"Organization: {summary_obj['package_structure']['organization']}\n"
                f"Rationale: {summary_obj['package_structure']['rationale']}\n"
                f"Cohesion: {summary_obj['package_structure']['cohesion_assessment']}\n"
            )
        
        # Architectural Insights
        if summary_obj.get('architectural_insights'):
            summary += "\nArchitectural Insights:\n"
            for insight in summary_obj['architectural_insights']:
                summary += f"  - {insight}\n"

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON response for package {package}. Using raw response.")
        summary = json_summary
    
    return summary

def main(project_root=None):
    parser = argparse.ArgumentParser(description="Gisting the Packages using LLM")
    if project_root is None:
        parser.add_argument("project_root", type=str, help="Path to the project root")
        args = parser.parse_args()
        project_root = args.project_root

    root_path = os.path.abspath(project_root)
    if not os.path.exists(root_path):
        print(f"Error: {root_path} does not exist")
        sys.exit(1)

    pf = ProjectFiles(
        repo_root_path=root_path,
    )

    # Load existing gist files and create package structure
    pf.from_gist_files()

    if not pf.files and not pf.resource_files:
        print("No gist files found. Please run gist_files.py first.")
        sys.exit(1)

    print("\n" + "-" * 50)
    print("Traversing Bottom-Up to generate package summaries:")
    print("-" * 50)

    # Create empty package notes file if it doesn't exist
    package_notes_path = os.path.join(root_path, pf.default_gist_foler, pf.default_package_notes_file)
    if not os.path.exists(package_notes_path):
        os.makedirs(os.path.dirname(package_notes_path), exist_ok=True)
        open(package_notes_path, 'w').close()
        print("Created new package notes file")

    # Initialize query manager with the ProjectFiles instance
    _query_manager = init_query_manager()
    _query_manager.pf = pf

    pf.package_gisting_func = real_package_gisting

    # Traverse and generate summaries, persisting after each package
    pf.package_structure_traverse(
        packages=None,
        action_file_func=pf.check_code_file_exists,
        action_package_func=pf.gist_package,
        is_bottom_up=True
    )

    print("\nPackage gisting complete!")
    print(f"Package summaries are available at: {package_notes_path}")

if __name__ == "__main__":
    main()
