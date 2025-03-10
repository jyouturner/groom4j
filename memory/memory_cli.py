#!/usr/bin/env python3
"""
CLI tool for managing the memory system.
This tool allows you to view, search, and manage memory entries for Java projects.
"""

import os
import sys
import argparse
import time
from datetime import datetime
import tabulate
import json
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our modules
from memory_manager import MemoryManager

def format_timestamp(timestamp):
    """Format a UNIX timestamp as a human-readable date/time"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def init_memory_manager(project_root):
    """Initialize the memory manager for a project"""
    try:
        # Load vector store configuration
        load_vector_store_config()
        
        # Initialize memory manager
        return MemoryManager(project_root=project_root)
    except Exception as e:
        logger.error(f"Error initializing memory manager: {str(e)}")
        sys.exit(1)

def list_memories(args):
    """List memories for a project"""
    memory_manager = init_memory_manager(args.project_root)
    
    # Get recent memories
    memories = memory_manager.get_recent_memories(
        limit=args.limit,
        entry_type=args.type
    )
    
    if not memories:
        print(f"No memories found for project {memory_manager.project_id}")
        return
    
    # Prepare table data
    table_data = []
    for memory in memories:
        table_data.append([
            memory['entry_id'][:8] + '...',
            memory['entry_type'],
            memory['question'][:50] + ('...' if len(memory['question']) > 50 else ''),
            format_timestamp(memory['timestamp']),
            len(memory['key_findings'])
        ])
    
    # Print table
    print(tabulate.tabulate(
        table_data,
        headers=['ID', 'Type', 'Question', 'Timestamp', 'Findings'],
        tablefmt='grid'
    ))
    
    print(f"\nTotal: {len(memories)} memories")
    print(f"Project ID: {memory_manager.project_id}")

def search_memories(args):
    """Search for memories by query"""
    memory_manager = init_memory_manager(args.project_root)
    
    # Search for similar memories
    similar_memories = memory_manager.find_similar_memories(
        query=args.query,
        entry_type=args.type,
        limit=args.limit,
        score_threshold=args.threshold
    )
    
    if not similar_memories:
        print(f"No similar memories found for query: {args.query}")
        return
    
    # Prepare table data
    table_data = []
    for i, memory in enumerate(similar_memories, 1):
        entry = memory.get('entry', {})
        score = memory.get('similarity_score', 0)
        
        table_data.append([
            i,
            f"{score:.2f}",
            entry.get('entry_type', ''),
            entry.get('question', '')[:50] + ('...' if len(entry.get('question', '')) > 50 else ''),
            format_timestamp(entry.get('timestamp', 0))
        ])
    
    # Print table
    print(tabulate.tabulate(
        table_data,
        headers=['#', 'Score', 'Type', 'Question', 'Timestamp'],
        tablefmt='grid'
    ))
    
    # If detailed view requested, show the full memory
    if args.view and similar_memories:
        view_memory(memory_manager, similar_memories[0].get('entry', {}).get('entry_id'))

def view_memory(memory_manager, memory_id):
    """View details of a specific memory"""
    entry = memory_manager.get_memory_by_id(memory_id)
    
    if not entry:
        print(f"Memory not found: {memory_id}")
        return
    
    print("\n" + "=" * 80)
    print(f"Memory ID: {entry.entry_id}")
    print(f"Project ID: {entry.project_id}")
    print(f"Type: {entry.entry_type}")
    print(f"Timestamp: {format_timestamp(entry.timestamp)}")
    print("=" * 80)
    
    print("\nQuestion:")
    print(entry.question)
    
    if entry.key_findings:
        print("\nKey Findings:")
        for finding in entry.key_findings:
            print(f"- {finding}")
    
    if entry.files_accessed:
        print("\nFiles Accessed:")
        for file in entry.files_accessed:
            print(f"- {file}")
    
    print("\nAnswer (excerpt):")
    # Print first 10 lines of answer
    answer_lines = entry.answer.split('\n')
    for line in answer_lines[:10]:
        print(line)
    if len(answer_lines) > 10:
        print("...")
        print(f"(Full answer has {len(answer_lines)} lines)")
    
    print("\n" + "=" * 80)

def view_memory_cmd(args):
    """Command handler for viewing a memory"""
    memory_manager = init_memory_manager(args.project_root)
    view_memory(memory_manager, args.id)

def delete_memory(args):
    """Delete a memory entry"""
    memory_manager = init_memory_manager(args.project_root)
    
    if args.all:
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete all memories for project {memory_manager.project_id}? [y/N] ")
        if confirm.lower() != 'y':
            print("Deletion cancelled")
            return
            
        # Delete all memories
        success = memory_manager.clear_project_memories(entry_type=args.type)
        if success:
            print(f"All memories deleted for project {memory_manager.project_id}")
        else:
            print("Failed to delete memories")
    else:
        # Delete specific memory
        if not args.id:
            print("Memory ID is required")
            return
            
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete memory {args.id}? [y/N] ")
        if confirm.lower() != 'y':
            print("Deletion cancelled")
            return
            
        # Delete memory
        success = memory_manager.delete_memory(args.id)
        if success:
            print(f"Memory {args.id} deleted")
        else:
            print(f"Failed to delete memory {args.id}")

def export_memories(args):
    """Export memories to a JSON file"""
    memory_manager = init_memory_manager(args.project_root)
    
    # Get memories
    memories = memory_manager.get_recent_memories(
        limit=args.limit if not args.all else 10000,
        entry_type=args.type
    )
    
    if not memories:
        print(f"No memories found for project {memory_manager.project_id}")
        return
    
    # Determine output file
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"memories_{memory_manager.project_id}_{timestamp}.json"
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            json.dump(memories, f, indent=2)
        print(f"Exported {len(memories)} memories to {output_file}")
    except Exception as e:
        print(f"Error exporting memories: {str(e)}")

def summarize_memories(args):
    """Generate a summary of project memories"""
    memory_manager = init_memory_manager(args.project_root)
    
    # Get summary
    summary = memory_manager.generate_memory_summary()
    print(summary)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Java Assistant Memory Management CLI")
    parser.add_argument('--project-root', '-p', type=str, default=os.getcwd(),
                       help="Root directory of the Java project")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List memories for a project')
    list_parser.add_argument('--limit', '-l', type=int, default=10,
                           help="Maximum number of memories to list")
    list_parser.add_argument('--type', '-t', type=str, default=None,
                           help="Filter by memory type (e.g., conversation, file_summary)")
    list_parser.set_defaults(func=list_memories)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for memories by query')
    search_parser.add_argument('query', type=str, help="Search query")
    search_parser.add_argument('--limit', '-l', type=int, default=5,
                             help="Maximum number of results")
    search_parser.add_argument('--threshold', '-th', type=float, default=0.7,
                             help="Similarity threshold (0.0 to 1.0)")
    search_parser.add_argument('--type', '-t', type=str, default=None,
                             help="Filter by memory type")
    search_parser.add_argument('--view', '-v', action='store_true',
                             help="View details of the top result")
    search_parser.set_defaults(func=search_memories)
    
    # View command
    view_parser = subparsers.add_parser('view', help='View a specific memory')
    view_parser.add_argument('id', type=str, help="Memory ID")
    view_parser.set_defaults(func=view_memory_cmd)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete memories')
    delete_parser.add_argument('--id', type=str, help="Memory ID to delete")
    delete_parser.add_argument('--all', '-a', action='store_true',
                             help="Delete all memories for the project")
    delete_parser.add_argument('--type', '-t', type=str, default=None,
                             help="Filter by memory type when deleting all")
    delete_parser.set_defaults(func=delete_memory)
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export memories to a file')
    export_parser.add_argument('--output', '-o', type=str,
                             help="Output file path (defaults to memories_<project-id>_<timestamp>.json)")
    export_parser.add_argument('--limit', '-l', type=int, default=100,
                             help="Maximum number of memories to export")
    export_parser.add_argument('--all', '-a', action='store_true',
                             help="Export all memories")
    export_parser.add_argument('--type', '-t', type=str, default=None,
                             help="Filter by memory type")
    export_parser.set_defaults(func=export_memories)
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Generate a summary of project memories')
    summary_parser.set_defaults(func=summarize_memories)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)

if __name__ == '__main__':
    main()