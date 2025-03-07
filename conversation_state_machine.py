from enum import Enum
import logging
import random
import time
import os
import json
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationState(Enum):
    # Basic conversation flow states
    INITIAL = "initial"               # First contact, no context
    EXPLORING = "exploring"           # Broad exploration of codebase
    FOCUSING = "focusing"             # Narrowing down on specific components
    ANALYZING = "analyzing"           # Deep analysis of selected components
    CLARIFYING = "clarifying"         # Resolving ambiguities
    SYNTHESIZING = "synthesizing"     # Creating comprehensive answers
    CONCLUDING = "concluding"         # Finalizing the response
    REFINING = "refining"             # Improving an existing answer
    
    # User expertise level states
    NOVICE_EXPLAINING = "novice_explaining"  # Simplified explanations for beginners
    EXPERT_DETAILING = "expert_detailing"    # Technical deep-dives for experts
    
    # Error handling states
    RECOVERY = "recovery"             # Handling unexpected inputs or errors
    FALLBACK = "fallback"             # Using simpler strategies when optimal fails
    
    # Meta states
    META_REFLECTION = "meta_reflection"  # Evaluating conversation quality
    STRATEGY_ADJUSTMENT = "strategy_adjustment"  # Changing approach mid-conversation
    
    # Special value for "any state" in transitions
    ANY = "any"  # Special token for any state

class StateTransition:
    def __init__(self, from_state, to_state, condition_fn):
        self.from_state = from_state
        self.to_state = to_state
        self.condition_fn = condition_fn
    
    def can_transition(self, conversation_context):
        return self.condition_fn(conversation_context)

class ConversationStateMachine:
    def __init__(self):
        self.current_state = ConversationState.INITIAL
        self.transitions = self._define_transitions()
        self.state_handlers = self._define_state_handlers()
        self.state_history = []
        self.transition_probabilities = self._initialize_transition_probabilities()
        self.parallel_tracks = {}  # For tracking multiple aspects of conversation
        
    def _define_transitions(self):
        # Define all valid state transitions with conditions
        return [
            # Regular flow transitions
            StateTransition(
                ConversationState.INITIAL,
                ConversationState.EXPLORING,
                lambda ctx: ctx.get("question_received", False)
            ),
            StateTransition(
                ConversationState.EXPLORING,
                ConversationState.FOCUSING,
                lambda ctx: ctx.get("relevant_components_found", False)
            ),
            StateTransition(
                ConversationState.EXPLORING,
                ConversationState.CLARIFYING,
                lambda ctx: ctx.get("ambiguities_detected", False)
            ),
            StateTransition(
                ConversationState.FOCUSING,
                ConversationState.ANALYZING,
                lambda ctx: ctx.get("components_selected", False)
            ),
            StateTransition(
                ConversationState.ANALYZING,
                ConversationState.SYNTHESIZING,
                lambda ctx: ctx.get("analysis_complete", False) or ctx.get("round", 0) > 3
            ),
            StateTransition(
                ConversationState.CLARIFYING,
                ConversationState.FOCUSING,
                lambda ctx: ctx.get("clarification_complete", False)
            ),
            StateTransition(
                ConversationState.SYNTHESIZING,
                ConversationState.CONCLUDING,
                lambda ctx: ctx.get("synthesis_complete", False) or 
                            ctx.get("current_thoroughness", 0) >= ctx.get("thoroughness_target", 6)
            ),
            StateTransition(
                ConversationState.CONCLUDING,
                ConversationState.REFINING,
                lambda ctx: ctx.get("refinement_requested", False)
            ),
            
            # Expertise level transitions
            StateTransition(
                ConversationState.FOCUSING,
                ConversationState.NOVICE_EXPLAINING,
                lambda ctx: ctx.get("user_expertise", "medium") == "beginner"
            ),
            StateTransition(
                ConversationState.FOCUSING,
                ConversationState.EXPERT_DETAILING,
                lambda ctx: ctx.get("user_expertise", "medium") == "expert"
            ),
            StateTransition(
                ConversationState.NOVICE_EXPLAINING,
                ConversationState.SYNTHESIZING,
                lambda ctx: ctx.get("explanation_complete", False) or ctx.get("round", 0) > 4
            ),
            StateTransition(
                ConversationState.EXPERT_DETAILING,
                ConversationState.SYNTHESIZING,
                lambda ctx: ctx.get("detailing_complete", False) or ctx.get("round", 0) > 5
            ),
            
            # Error handling transitions
            StateTransition(
                ConversationState.ANY,
                ConversationState.RECOVERY,
                lambda ctx: ctx.get("error_detected", False)
            ),
            StateTransition(
                ConversationState.ANY,
                ConversationState.FALLBACK,
                lambda ctx: ctx.get("confidence", 1.0) < 0.3
            ),
            StateTransition(
                ConversationState.RECOVERY,
                ConversationState.EXPLORING,
                lambda ctx: ctx.get("error_handled", False)
            ),
            StateTransition(
                ConversationState.FALLBACK,
                ConversationState.EXPLORING,
                lambda ctx: ctx.get("using_fallback", True) and ctx.get("round", 0) > ctx.get("fallback_round", 0) + 1
            ),
            
            # Meta-transitions
            StateTransition(
                ConversationState.ANY,
                ConversationState.META_REFLECTION,
                lambda ctx: ctx.get("round", 0) % 3 == 0 and ctx.get("round", 0) > 0  # Every 3 rounds
            ),
            StateTransition(
                ConversationState.META_REFLECTION,
                ConversationState.STRATEGY_ADJUSTMENT,
                lambda ctx: ctx.get("strategy_adjustment", None) is not None
            ),
            StateTransition(
                ConversationState.STRATEGY_ADJUSTMENT,
                ConversationState.EXPLORING,
                lambda ctx: True  # Always return to exploring after strategy adjustment
            ),
        ]
    
    def _define_state_handlers(self):
        # Map states to handler functions
        return {
            ConversationState.INITIAL: self._handle_initial,
            ConversationState.EXPLORING: self._handle_exploring,
            ConversationState.FOCUSING: self._handle_focusing,
            ConversationState.ANALYZING: self._handle_analyzing,
            ConversationState.CLARIFYING: self._handle_clarifying,
            ConversationState.SYNTHESIZING: self._handle_synthesizing,
            ConversationState.CONCLUDING: self._handle_concluding,
            ConversationState.REFINING: self._handle_refining,
            ConversationState.NOVICE_EXPLAINING: self._handle_novice_explaining,
            ConversationState.EXPERT_DETAILING: self._handle_expert_detailing,
            ConversationState.RECOVERY: self._handle_recovery,
            ConversationState.FALLBACK: self._handle_fallback,
            ConversationState.META_REFLECTION: self._handle_meta_reflection,
            ConversationState.STRATEGY_ADJUSTMENT: self._handle_strategy_adjustment,
        }
    
    def _initialize_transition_probabilities(self):
        """Initialize transition probability matrix based on predefined weights"""
        states = list(ConversationState)
        # Create a matrix of transition probabilities
        matrix = {s1: {s2: 0.0 for s2 in states} for s1 in states}
        
        # Set initial probabilities based on expected flow
        # These will be updated based on actual usage patterns
        matrix[ConversationState.INITIAL][ConversationState.EXPLORING] = 1.0
        matrix[ConversationState.EXPLORING][ConversationState.FOCUSING] = 0.7
        matrix[ConversationState.EXPLORING][ConversationState.CLARIFYING] = 0.3
        matrix[ConversationState.FOCUSING][ConversationState.ANALYZING] = 0.6
        matrix[ConversationState.FOCUSING][ConversationState.NOVICE_EXPLAINING] = 0.2
        matrix[ConversationState.FOCUSING][ConversationState.EXPERT_DETAILING] = 0.2
        matrix[ConversationState.ANALYZING][ConversationState.SYNTHESIZING] = 1.0
        matrix[ConversationState.CLARIFYING][ConversationState.FOCUSING] = 1.0
        matrix[ConversationState.SYNTHESIZING][ConversationState.CONCLUDING] = 1.0
        matrix[ConversationState.CONCLUDING][ConversationState.REFINING] = 0.3
        matrix[ConversationState.NOVICE_EXPLAINING][ConversationState.SYNTHESIZING] = 1.0
        matrix[ConversationState.EXPERT_DETAILING][ConversationState.SYNTHESIZING] = 1.0
        matrix[ConversationState.RECOVERY][ConversationState.EXPLORING] = 1.0
        matrix[ConversationState.FALLBACK][ConversationState.EXPLORING] = 1.0
        matrix[ConversationState.META_REFLECTION][ConversationState.STRATEGY_ADJUSTMENT] = 0.5
        matrix[ConversationState.META_REFLECTION][ConversationState.EXPLORING] = 0.5
        matrix[ConversationState.STRATEGY_ADJUSTMENT][ConversationState.EXPLORING] = 1.0
        
        return matrix
    
    def update_transition_probabilities(self, from_state, to_state, success_factor=1.0):
        """Update transition probabilities based on successful transitions"""
        # Increase probability for successful transitions
        current_prob = self.transition_probabilities[from_state][to_state]
        # Apply simple reinforcement
        self.transition_probabilities[from_state][to_state] = current_prob + 0.1 * success_factor
        
        # Normalize to ensure probabilities sum to 1
        total = sum(self.transition_probabilities[from_state].values())
        if total > 0:  # Avoid division by zero
            for state in self.transition_probabilities[from_state]:
                self.transition_probabilities[from_state][state] /= total
    
    def begin_parallel_track(self, track_name, initial_state=ConversationState.INITIAL):
        """Begin a parallel conversation track for a specific aspect"""
        self.parallel_tracks[track_name] = {
            "state": initial_state,
            "history": [],
            "context": {}
        }
    
    def process_parallel_track(self, track_name, context):
        """Process a specific conversation track"""
        if track_name not in self.parallel_tracks:
            self.begin_parallel_track(track_name)
            
        track = self.parallel_tracks[track_name]
        old_state = track["state"]
        
        # Find transitions for this track's state
        valid_transitions = [
            t for t in self.transitions 
            if (t.from_state == old_state or t.from_state == ConversationState.ANY) 
            and t.can_transition(context)
        ]
        
        # Select next state using probabilities as weights
        if valid_transitions:
            # Use transition probabilities to weight selection
            weights = [self.transition_probabilities[old_state][t.to_state] for t in valid_transitions]
            next_transition = random.choices(valid_transitions, weights=weights, k=1)[0]
            track["state"] = next_transition.to_state
            track["history"].append((old_state, track["state"]))
            
        # Execute handler and update track context
        result = self.state_handlers[track["state"]](context)
        track["context"].update(result.get("context_updates", {}))
        
        return result
    
    def process(self, conversation_context):
        """Process the main conversation state machine"""
        old_state = self.current_state
        self.state_history.append(old_state)
        
        # Find valid transitions from current state
        valid_transitions = [
            t for t in self.transitions 
            if (t.from_state == self.current_state or t.from_state == ConversationState.ANY) 
            and t.can_transition(conversation_context)
        ]
        
        # Select next state using probabilities and fallback mechanism
        next_state = None
        if valid_transitions:
            # Use transition probabilities to weight selection
            weights = [self.transition_probabilities[old_state][t.to_state] for t in valid_transitions]
            next_transition = random.choices(valid_transitions, weights=weights, k=1)[0]
            next_state = next_transition.to_state
        else:
            # Fallback mechanism if no valid transitions
            logger.warning(f"No valid transitions from {self.current_state}. Using fallback.")
            next_state = ConversationState.FALLBACK
        
        # Update state and record transition
        if next_state:
            self.current_state = next_state
            logger.info(f"State transition: {old_state} -> {self.current_state}")
            
            # Update transition probabilities based on outcome
            # Will be implemented after execution to determine success
        
        # Execute handler for current state
        result = self.state_handlers[self.current_state](conversation_context)
        
        # Update transition probabilities based on successful execution
        success_factor = result.get("success_factor", 0.5)  # Default middling success
        self.update_transition_probabilities(old_state, self.current_state, success_factor)
        
        return result
    
    def revert_to_previous_state(self, context):
        """Revert to previous state if current approach is not working"""
        if len(self.state_history) > 1:
            # Get the previous state (not the current one which is already in history)
            previous_state = self.state_history[-1]  # This is actually the current state
            # The state before that is the one we want to revert to
            if len(self.state_history) > 1:
                previous_state = self.state_history[-2]  # This is the actual previous state
            
            logger.info(f"Reverting to previous state: {previous_state}")
            self.current_state = previous_state
            # Remove the current state from history since we're reverting
            if self.state_history:
                self.state_history.pop()
            
            return self.state_handlers[self.current_state](context)
        return self.state_handlers[self.current_state](context)
    
    # Handler implementations
    def _handle_initial(self, context):
        # Logic for initial state
        return {
            "prompt_guidance": "Establish initial context",
            "context_updates": {"state_processed": True, "question_received": True},
            "success_factor": 1.0
        }
    
    def _handle_exploring(self, context):
        # Logic for exploring state
        return {
            "prompt_guidance": "Discover relevant components",
            "context_updates": {"explored_components": context.get("explored_components", [])},
            "success_factor": 0.8
        }
        
    def _handle_focusing(self, context):
        # Logic for focusing state
        return {
            "prompt_guidance": "Analyze specific components",
            "context_updates": {"focused_on": context.get("selected_component")},
            "success_factor": 0.9
        }
    
    def _handle_analyzing(self, context):
        return {
            "prompt_guidance": "Perform detailed analysis of focused components",
            "context_updates": {
                "analysis_progress": min(100, context.get("analysis_progress", 0) + 25),
                "analysis_complete": context.get("analysis_progress", 0) >= 75
            },
            "success_factor": 0.85
        }
    
    def _handle_clarifying(self, context):
        return {
            "prompt_guidance": "Resolve ambiguities in the question",
            "context_updates": {
                "clarification_progress": min(100, context.get("clarification_progress", 0) + 30),
                "clarification_complete": context.get("clarification_progress", 0) >= 90
            },
            "success_factor": 0.75
        }
    
    def _handle_synthesizing(self, context):
        return {
            "prompt_guidance": "Synthesize findings into a comprehensive answer",
            "context_updates": {
                "synthesis_progress": min(100, context.get("synthesis_progress", 0) + 35),
                "synthesis_complete": context.get("synthesis_progress", 0) >= 85
            },
            "success_factor": 0.9
        }
    
    def _handle_concluding(self, context):
        return {
            "prompt_guidance": "Provide final conclusions and summary",
            "context_updates": {"conclusion_provided": True},
            "success_factor": 0.95
        }
    
    def _handle_refining(self, context):
        return {
            "prompt_guidance": "Refine the answer based on additional context",
            "context_updates": {"refinement_applied": True},
            "success_factor": 0.85
        }
    
    def _handle_novice_explaining(self, context):
        return {
            "prompt_guidance": "Simplify explanations, use analogies",
            "context_updates": {
                "explanation_level": "basic",
                "explanation_progress": min(100, context.get("explanation_progress", 0) + 30),
                "explanation_complete": context.get("explanation_progress", 0) >= 90
            },
            "success_factor": 0.95
        }
    
    def _handle_expert_detailing(self, context):
        return {
            "prompt_guidance": "Provide technical details and implementation specifics",
            "context_updates": {
                "explanation_level": "advanced",
                "detailing_progress": min(100, context.get("detailing_progress", 0) + 25),
                "detailing_complete": context.get("detailing_progress", 0) >= 90
            },
            "success_factor": 0.9
        }
    
    def _handle_recovery(self, context):
        return {
            "prompt_guidance": "Recover from error, clarify understanding",
            "context_updates": {"error_handled": True, "error_detected": False},
            "success_factor": 0.6
        }
    
    def _handle_fallback(self, context):
        return {
            "prompt_guidance": "Use simpler approach, focus on basics",
            "context_updates": {"using_fallback": True, "fallback_round": context.get("round", 0)},
            "success_factor": 0.5
        }
    
    def _handle_meta_reflection(self, context):
        # Evaluate conversation quality and adjust strategy
        thoroughness = context.get("current_thoroughness", 0)
        rounds_left = context.get("max_rounds", 8) - context.get("round", 0)
        
        strategy_adjustment = None
        if thoroughness < 3 and rounds_left > 2:
            strategy_adjustment = "broaden_search"
        elif thoroughness > 7:
            strategy_adjustment = "start_concluding"
            
        return {
            "prompt_guidance": "Reflect on conversation progress",
            "context_updates": {"strategy_adjustment": strategy_adjustment},
            "success_factor": 0.8
        }
    
    def _handle_strategy_adjustment(self, context):
        adjustment = context.get("strategy_adjustment")
        
        if adjustment == "broaden_search":
            guidance = "Expand search scope to explore more components"
        elif adjustment == "start_concluding":
            guidance = "Begin synthesizing findings into final answer"
        else:
            guidance = "Adjust approach based on current progress"
            
        return {
            "prompt_guidance": guidance,
            "context_updates": {"strategy_applied": adjustment},
            "success_factor": 0.7
        }

# State-specific prompt templates
STATE_PROMPTS = {
    # Core conversation flow prompts
    ConversationState.EXPLORING: """
You are in the EXPLORING phase. Focus on:
- Understanding the high-level structure of the codebase
- Identifying key components related to the user's question
- Determining which files to examine in more detail

Current question: {question}
Project context: {project_context}
User expertise level: {user_expertise}
    """,
    
    ConversationState.FOCUSING: """
You are in the FOCUSING phase. Focus on:
- Examining specific components in detail
- Understanding interconnections between components
- Identifying the most relevant code sections

Current question: {question}
Project context: {project_context}
Explored components: {explored_components}
    """,
    
    ConversationState.ANALYZING: """
You are in the ANALYZING phase. Focus on:
- Deep analysis of the selected components
- Understanding implementation details
- Tracing data flow and control flow

Current question: {question}
Components being analyzed: {focused_components}
Related files: {related_files}
    """,
    
    ConversationState.CLARIFYING: """
You are in the CLARIFYING phase. Focus on:
- Resolving ambiguities in the user's question
- Determining what specific information is needed
- Asking follow-up questions if necessary

Current question: {question}
Ambiguities identified: {ambiguities}
Areas needing clarification: {clarification_needed}
    """,
    
    ConversationState.SYNTHESIZING: """
You are in the SYNTHESIZING phase. Focus on:
- Combining information from multiple sources
- Creating a comprehensive answer
- Ensuring all aspects of the question are addressed

Current question: {question}
Key findings: {key_findings}
Remaining gaps: {information_gaps}
    """,
    
    ConversationState.CONCLUDING: """
You are in the CONCLUDING phase. Focus on:
- Finalizing your response with clear conclusions
- Summarizing key points
- Suggesting next steps or related information

Current question: {question}
Key conclusions: {conclusions}
    """,
    
    # User expertise level prompts
    ConversationState.NOVICE_EXPLAINING: """
You are in the NOVICE_EXPLAINING phase. The user has beginner-level expertise. Focus on:
- Using simple, clear language without jargon
- Providing analogies and examples
- Explaining concepts step-by-step
- Avoiding technical implementation details unless asked

Current question: {question}
Key concepts to explain: {key_concepts}
    """,
    
    ConversationState.EXPERT_DETAILING: """
You are in the EXPERT_DETAILING phase. The user has expert-level expertise. Focus on:
- Providing detailed technical information
- Discussing implementation specifics
- Analyzing edge cases and performance considerations
- Referencing design patterns and advanced concepts

Current question: {question}
Technical areas to detail: {technical_details}
Edge cases to consider: {edge_cases}
    """,
    
    # Error handling prompts
    ConversationState.RECOVERY: """
You are in the RECOVERY phase. An error or misunderstanding has occurred. Focus on:
- Identifying the source of confusion
- Correcting any misunderstandings
- Resetting analysis with clearer parameters
- Acknowledging limitations if necessary

Current question: {question}
Error context: {error_context}
Previous approach: {previous_approach}
    """,
    
    ConversationState.FALLBACK: """
You are in the FALLBACK phase. Confidence is low or approach isn't working. Focus on:
- Using a simpler, more direct approach
- Focusing on established facts
- Being transparent about limitations
- Offering alternative approaches

Current question: {question}
Current limitations: {limitations}
Alternative approaches: {alternatives}
    """,
    
    # Meta-reflection prompts
    ConversationState.META_REFLECTION: """
You are in the META_REFLECTION phase. Evaluate conversation progress. Focus on:
- Assessing the quality of information gathered
- Identifying remaining knowledge gaps
- Determining if the conversation is on track
- Considering strategy adjustments

Current question: {question}
Current thoroughness: {current_thoroughness}/10
Rounds remaining: {rounds_remaining}
Strategy adjustment: {strategy_adjustment}
    """,
    
    ConversationState.STRATEGY_ADJUSTMENT: """
You are in the STRATEGY_ADJUSTMENT phase. The current approach needs modification. Focus on:
- Implementing the strategy change
- Broadening or narrowing scope as appropriate
- Changing information gathering tactics
- Setting expectations for the new approach

Current question: {question}
Previous strategy: {previous_strategy}
New strategy: {new_strategy}
Reason for change: {change_reason}
    """
}

def generate_prompt_for_state(state, context):
    """Generate appropriate prompt for the current conversation state"""
    # Get the base template or fallback to EXPLORING if not found
    template = STATE_PROMPTS.get(state, STATE_PROMPTS[ConversationState.EXPLORING])
    
    # Add standard elements to all prompts
    standard_context = {
        "conversation_round": context.get("round", 0),
        "max_rounds": context.get("max_rounds", 8),
        "state_history": context.get("state_history", []),
        "user_expertise": context.get("user_expertise", "medium"),
    }
    
    # Merge standard context with provided context
    merged_context = {**standard_context, **context}
    
    # Generate the prompt with all context variables
    try:
        formatted_prompt = template.format(**merged_context)
    except KeyError as e:
        # Handle missing context variables gracefully
        logger.warning(f"Missing context variable in prompt template: {e}")
        # Add placeholder for missing variable
        merged_context[str(e).strip("'")] = f"[Missing: {e}]"
        formatted_prompt = template.format(**merged_context)
    
    # Add state persistence instructions for all prompts
    formatted_prompt += """
---
Conversation State Information:
- Current state: {current_state}
- Previous state: {previous_state}
- Transition reason: {transition_reason}

Remember to maintain state context across interactions by referencing 
previous findings and building upon them progressively.
""".format(
        current_state=state.value,
        previous_state=context.get("previous_state", "none"),
        transition_reason=context.get("transition_reason", "initial")
    )
    
    return formatted_prompt

def generate_multi_track_prompt(main_state, parallel_tracks, context):
    """Generate a prompt that combines information from multiple conversation tracks"""
    main_prompt = generate_prompt_for_state(main_state, context)
    
    track_sections = []
    for track_name, track_data in parallel_tracks.items():
        track_state = track_data["state"]
        track_context = track_data["context"]
        track_sections.append(f"""
--- Track: {track_name} ({track_state.value}) ---
{generate_prompt_for_state(track_state, track_context).split('---')[0].strip()}
        """)
    
    if track_sections:
        main_prompt += "\n\n=== PARALLEL TRACKS ===\n" + "\n".join(track_sections)
    
    return main_prompt

class StateCache:
    def __init__(self):
        self.cache = {state: {} for state in ConversationState}
        self.expiration = {state: {} for state in ConversationState}
        self.max_age = 3600  # Default 1 hour expiration
    
    def get(self, state, key, default=None):
        """Get a value from the cache with expiration check"""
        if state not in self.cache or key not in self.cache[state]:
            return default
            
        # Check if entry has expired
        if key in self.expiration[state]:
            if time.time() > self.expiration[state][key]:
                # Expired entry
                del self.cache[state][key]
                del self.expiration[state][key]
                return default
                
        return self.cache[state].get(key, default)
    
    def set(self, state, key, value, ttl=None):
        """Set a value in the cache with optional time-to-live"""
        self.cache[state][key] = value
        
        # Set expiration if ttl is provided
        if ttl:
            self.expiration[state][key] = time.time() + ttl
        else:
            self.expiration[state][key] = time.time() + self.max_age
    
    def invalidate(self, state=None, key=None):
        """Invalidate specific cache entries or entire state caches"""
        if state is None:
            # Clear entire cache
            self.cache = {state: {} for state in ConversationState}
            self.expiration = {state: {} for state in ConversationState}
        elif key is None:
            # Clear entire state cache
            self.cache[state] = {}
            self.expiration[state] = {}
        else:
            # Clear specific key
            if key in self.cache[state]:
                del self.cache[state][key]
            if key in self.expiration[state]:
                del self.expiration[state][key]

class StateManager:
    """Central manager for conversation state and persistence"""
    def __init__(self):
        self.state_machine = ConversationStateMachine()
        self.cache = StateCache()
        self.conversation_history = []
        self.session_storage = {}  # For session-level persistence
        
    def persist_session(self, path):
        """Save session state to disk for later restoration"""
        persistent_data = {
            "state_history": [s.value for s in self.state_machine.state_history],
            "current_state": self.state_machine.current_state.value,
            "session_storage": self.session_storage,
            "transition_probabilities": {
                k.value: {k2.value: v2 for k2, v2 in v.items()} 
                for k, v in self.state_machine.transition_probabilities.items()
            },
            "conversation_summary": self._generate_conversation_summary()
        }
        
        with open(path, 'w') as f:
            json.dump(persistent_data, f)
    
    def restore_session(self, path):
        """Restore session state from disk"""
        if not os.path.exists(path):
            return False
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            # Restore state machine
            self.state_machine.current_state = ConversationState(data["current_state"])
            self.state_machine.state_history = [ConversationState(s) for s in data.get("state_history", [])]
            
            # Restore probabilities if available
            if "transition_probabilities" in data:
                # Convert string keys back to enum objects
                restored_probs = {}
                for from_state_str, targets in data["transition_probabilities"].items():
                    from_state = ConversationState(from_state_str)
                    restored_probs[from_state] = {}
                    for to_state_str, prob in targets.items():
                        restored_probs[from_state][ConversationState(to_state_str)] = prob
                self.state_machine.transition_probabilities = restored_probs
            
            # Restore session storage
            self.session_storage = data.get("session_storage", {})
            
            return True
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
            return False
    
    def _generate_conversation_summary(self):
        """Generate a summary of the conversation for persistence"""
        if not self.conversation_history:
            return ""
            
        # Use LLM to generate a summary if appropriate
        # For simplicity, just return the last few turns
        return {
            "last_question": self.conversation_history[-2]["content"] 
                if len(self.conversation_history) > 1 else "",
            "last_answer": self.conversation_history[-1]["content"] 
                if self.conversation_history else "",
            "key_findings": self.session_storage.get("key_findings", []),
            "state_sequence": [s.value for s in self.state_machine.state_history[-5:]]
        }
    
    def get_thoroughness_target_for_state(self, state):
        """Get appropriate thoroughness target based on state"""
        # Different states have different thoroughness requirements
        targets = {
            ConversationState.INITIAL: 3,
            ConversationState.EXPLORING: 5,
            ConversationState.FOCUSING: 6,
            ConversationState.ANALYZING: 8,
            ConversationState.CLARIFYING: 4,
            ConversationState.SYNTHESIZING: 7,
            ConversationState.CONCLUDING: 9,
            ConversationState.NOVICE_EXPLAINING: 6,
            ConversationState.EXPERT_DETAILING: 9,
            ConversationState.FALLBACK: 4,
        }
        return targets.get(state, 6)  # Default to 6 for unlisted states
    
    def update_conversation_history(self, speaker, content, state=None):
        """Add an entry to the conversation history"""
        if not state and speaker == "assistant":
            state = self.state_machine.current_state
            
        entry = {
            "speaker": speaker,
            "content": content,
            "timestamp": time.time()
        }
        
        if state:
            entry["state"] = state.value
            
        self.conversation_history.append(entry)
        
    def log_state_transition(self, old_state, new_state, reason=""):
        """Log a state transition for visualization"""
        logger.info(f"State transition: {old_state.value} -> {new_state.value} (Reason: {reason})")
        self.session_storage.setdefault("transitions", []).append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": time.time()
        })

class UserProfile:
    """Tracks user preferences and expertise levels"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.expertise_level = "medium"  # default, beginner, medium, expert
        self.preferred_detail_level = "balanced"  # brief, balanced, detailed
        self.recent_topics = []
        self.feedback_history = {}  # Track what types of responses the user prefers
    
    def update_expertise(self, topic, level):
        """Update user expertise for a specific topic"""
        # Could store as {topic: level} or use a more sophisticated model
        self.expertise_level = level
    
    def update_from_feedback(self, response_id, feedback_score):
        """Update preferences based on user feedback"""
        self.feedback_history[response_id] = feedback_score
        # Analyze patterns in feedback to adjust preferences
        
    def get_context_for_prompt(self):
        """Get user profile information to add to prompt context"""
        return {
            "user_expertise": self.expertise_level,
            "detail_preference": self.preferred_detail_level,
            "recent_topics": self.recent_topics[-3:],  # Last 3 topics
        }

def detect_related_conversation(current_question, prev_sessions):
    """Determine if the current question is related to a previous session"""
    # Simplified approach using basic keyword matching
    current_words = set(current_question.lower().split())
    
    for session in prev_sessions:
        prev_question = session.get("last_question", "")
        if not prev_question:
            continue
            
        prev_words = set(prev_question.lower().split())
        # Calculate Jaccard similarity
        intersection = len(current_words.intersection(prev_words))
        union = len(current_words.union(prev_words))
        
        if union > 0 and intersection / union > 0.5:  # Threshold for similarity
            return session["id"]
    
    return None

def generate_state_transition_diagram(conversation_history):
    """Generate a mermaid.js diagram of state transitions for the conversation"""
    transitions = []
    states_seen = set()
    
    for i in range(len(conversation_history) - 1):
        if "state" not in conversation_history[i] or "state" not in conversation_history[i + 1]:
            continue
            
        from_state = conversation_history[i]["state"]
        to_state = conversation_history[i + 1]["state"]
        reason = conversation_history[i + 1].get("transition_reason", "")
        
        transitions.append((from_state, to_state, reason))
        states_seen.add(from_state)
        states_seen.add(to_state)
    
    # Generate mermaid.js stateDiagram syntax
    mermaid_code = "stateDiagram-v2\n"
    
    # Define states
    for state in states_seen:
        mermaid_code += f"    {state}\n"
    
    # Define transitions
    for from_state, to_state, reason in transitions:
        if reason:
            mermaid_code += f"    {from_state} --> {to_state}: {reason}\n"
        else:
            mermaid_code += f"    {from_state} --> {to_state}\n"
    
    return mermaid_code

def save_conversation_with_states(conversation, filename):
    """Save conversation history with state information to a file"""
    with open(filename, 'w') as f:
        f.write("# Conversation with State Tracking\n\n")
        
        for i, turn in enumerate(conversation):
            state = turn.get("state", "unknown")
            speaker = turn.get("speaker", "User" if i % 2 == 0 else "Assistant")
            content = turn.get("content", "")
            
            f.write(f"## Turn {i+1} ({speaker}, State: {state})\n\n")
            f.write(f"{content}\n\n")
            
            # Add state transition information
            if i > 0 and speaker == "assistant":  # Only for assistant turns
                prev_state = conversation[i-1].get("state", "unknown") if i >= 1 else "none"
                if prev_state != state:
                    f.write(f"*State transition: {prev_state} → {state}*\n")
                    if "transition_reason" in turn:
                        f.write(f"*Reason: {turn['transition_reason']}*\n")
                    f.write("\n---\n\n")