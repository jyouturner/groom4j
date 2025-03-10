# Gist - Java Project Analysis Tool

Gist is a tool for analyzing Java projects to extract semantic meaning from code files and package structures. It uses LLMs (Large Language Models) to generate comprehensive summaries of Java files and packages, helping developers understand complex codebases more efficiently.

## Overview

This package provides tools to:

1. Analyze individual Java files to extract their purpose, structure, and relationships
2. Analyze package structures to understand architectural patterns and component interactions
3. Persist analysis results for future reference

## Components

### Core Classes

- `ProjectFiles`: Main class for managing project file analysis and persistence
- `CodeFile`: Represents a single code file with its metadata and summary
- `FilePersistence`: Abstract interface for persisting analysis results
- `DefaultFilePersistence`: Default implementation of the persistence interface

### Main Modules

- `gist_files.py`: Analyzes individual code files using LLMs
- `gist_packages.py`: Analyzes package structures using LLMs
- `__main__.py`: Command-line interface for running the tool

### Prompt Templates

- `java-semantic-analysis-phase1-prompt.md`: Template for Java file analysis
- `package-semantic-analysis-prompt.md`: Template for package analysis

## Usage

### Command Line

```bash
# Analyze files in a Java project
python -m gist files /path/to/java/project

# Analyze package structure (run after analyzing files)
python -m gist packages /path/to/java/project
```

### As a Library

```python
from gist import ProjectFiles

# Initialize with project root
pf = ProjectFiles(repo_root_path="/path/to/java/project")

# Analyze project files
pf.from_project()

# Access file summaries
for file in pf.files:
    print(f"{file.filename}: {file.summary}")

# Access package structure
print(pf.to_tree())
```

## File Analysis Process

1. The tool scans the project directory for Java files
2. Each file is analyzed using an LLM with a specialized prompt
3. The analysis extracts:
   - File type (Service, Controller, Model, etc.)
   - Primary responsibility
   - Implemented interfaces and extended classes
   - Key operations and dependencies
   - Architectural patterns

## Package Analysis Process

1. After file analysis is complete, package analysis begins
2. The tool traverses the package structure bottom-up
3. For each package, it analyzes:
   - Package purpose and architectural role
   - Component relationships and data flows
   - Design patterns and architectural insights
   - Service orchestration and cross-cutting concerns

## Output

Analysis results are stored in the `.gist` directory within your project:

- `code_files.txt`: Contains summaries of all analyzed files
- `package_notes.txt`: Contains summaries of all analyzed packages

## Dependencies

- Requires access to an LLM service (configured through environment variables)
- Uses the `config_utils`, `llm_client`, and `llm_utils` modules for LLM integration
