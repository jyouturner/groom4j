# Conversation Review System

The conversation review system is a crucial component that determines when an AI conversation should end. It ensures conversations are both thorough and efficient by monitoring progress and preventing unnecessary repetition.

## How It Works

### 1. Core Components

The system consists of three main components:

- **ConversationReviewer**: Manages conversation history and makes decisions about continuing or concluding
- **LLM Interaction Layer**: Handles the actual conversation flow and new information gathering
- **Review Decision Process**: Uses a tier2 LLM to evaluate conversation progress

### 2. Decision Flow

The conversation review system follows a structured decision flow:

1. **Initial Check**:
   - If no new information is found, the conversation ends
   - If new information is found, the conversation continues

### 3. Termination Conditions

A conversation can end for any of these reasons:

1. **No New Information Available**
   - When the system can't find any new relevant files, packages, or information
   - ```python
     if not new_information:
         return False, None
     ```

2. **Thoroughness Target Met**
   - Each conversation has a target thoroughness score (default: 6/10)
   - The reviewer monitors progress toward this target
   - ```python
     target_thoroughness = 6  # Can be configured (1-10)
     ```

3. **Reviewer Decision**
   - A tier2 LLM evaluates the conversation based on:
     - Progress toward answering the question
     - Signs of repetition or being stuck
     - Value of continuing vs concluding
     - Current thoroughness score

### 4. Configuration

You can configure the review system through several parameters:

- **Target Thoroughness**: The minimum score required to continue the conversation
- **Max Iterations**: The maximum number of iterations allowed
- **Termination Conditions**: The conditions that can end the conversation

### 5. Usage

The conversation review system is used in the `should_continue_conversation` function.

```python
should_continue, final_answer_prompt = conversation_reviewer.should_continue_conversation()
```

