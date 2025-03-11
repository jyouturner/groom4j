import sys
import argparse
from .gist_files import main as gist_files_main
from .gist_packages import main as gist_packages_main

def main():
    parser = argparse.ArgumentParser(description="Java project analysis tool")
    parser.add_argument("command", choices=["files", "packages"], 
                       help="Analysis type: 'files' for file analysis, 'packages' for package analysis")
    parser.add_argument("project_root", help="Path to the Java project root")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.command == "files":
        gist_files_main(args.project_root)
    elif args.command == "packages":
        gist_packages_main(args.project_root)
    else:
        print(f"Unknown command: {args.command}")
        print("Available commands: files, packages")
        sys.exit(1)

if __name__ == "__main__":
    main() 