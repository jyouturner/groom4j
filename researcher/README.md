# Researcher Package

The researcher package is a core component of Groom4J that handles intelligent code analysis and question answering through LLM interactions. It implements a sophisticated conversation system that can break down complex questions, explore codebases, and provide comprehensive answers.

## 🌟 Key Components

### 1. LLM Interaction (`llm_interaction.py`)
- Manages interactions with Language Learning Models (LLMs)
- Processes responses and extracts key findings
- Handles file and package requests
- Maintains conversation state and search history
- Implements retry mechanisms for failed requests

### 2. Conversation Reviewer (`conversation_reviewer.py`)
- Evaluates conversation quality and progress
- Manages conversation state transitions
- Tracks thoroughness of responses (1-10 scale)
- Provides guidance for continuing or concluding conversations
- Integrates with memory system for persistent storage

### 3. Question Rewriter (`rewrite_question.py`)
- Breaks down complex questions into smaller, manageable components
- Refines questions for more focused analysis
- Provides structured approach to complex inquiries
- Generates analysis strategies for decomposed questions

### 4. Functions (`functions.py`)
- Core utilities for file and package operations
- Search functionality for codebase exploration
- File content retrieval and processing
- Package information gathering
- Memory management utilities

## 🔄 Workflow

1. **Question Processing**
   - Questions are received and optionally decomposed
   - Previous relevant conversations are retrieved from memory
   - Initial search strategy is formulated

2. **Exploration Phase**
   - Systematic codebase exploration
   - File content retrieval and analysis
   - Package structure examination
   - Key finding extraction and tracking

3. **Synthesis Phase**
   - Information consolidation
   - Pattern recognition
   - Cross-reference with previous findings
   - Generation of comprehensive answers

4. **Review and Conclusion**
   - Quality assessment of responses
   - Thoroughness evaluation
   - State-based conversation management
   - Memory persistence of valuable insights

## 💡 Key Features

- **Intelligent Question Decomposition**: Breaks down complex queries into manageable sub-questions
- **State Machine Management**: Tracks conversation flow through various states
- **Memory Integration**: Stores and retrieves relevant past conversations
- **Tiered LLM Approach**: Uses different LLM tiers for various tasks
- **Robust Error Handling**: Implements retry mechanisms and fallbacks
- **Thorough Documentation**: Maintains clear tracking of findings and decisions

## 🔍 Search Strategies

The package implements sophisticated search strategies:
- Multiple keyword variations
- Context-aware file exploration
- Package hierarchy analysis
- Cross-reference detection
- Pattern matching for related components

## 📊 Key Finding Categories

Findings are categorized with specific tags:
- `[BUSINESS_RULE]`: Business logic and rules
- `[IMPLEMENTATION_DETAIL]`: Technical implementation specifics
- `[DATA_FLOW]`: Data movement and processing
- `[ARCHITECTURE]`: System design decisions
- `[SPECIAL_CASE]`: Exception handling and edge cases
- `[COMPARISON]`: Comparative analysis
- `[CODE_VALUES]`: Important constants and values
- `[EVOLUTION]`: Implementation changes over time
- `[IDENTIFIER]`: Important identifiers and references

## 🔧 Configuration

The package can be configured through:
- LLM provider selection
- Memory system settings
- Thoroughness thresholds
- Maximum conversation rounds
- State transition rules

## 🧪 Testing

Comprehensive test suite available:
- `test_conversation_reviewer.py`
- `test_llm_interaction.py`
- `test_llm_interaction_2.py`

## 📚 Usage Example

```python
from researcher.main import answer_question
from gist.projectfiles import ProjectFiles

# Initialize project files
pf = ProjectFiles(repo_root_path="path/to/project")
pf.from_gist_files()

# Ask a question about the codebase
response, reviewer = answer_question(
    pf=pf,
    question="How does the authentication system work?",
    thoroughness=8,
    max_rounds=10
)

# Access conversation history and findings
key_findings = reviewer.current_key_findings
conversation_state = reviewer.get_current_state()
``` 