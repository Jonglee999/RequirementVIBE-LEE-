"""
Prompt Service for ReqVibe

Character prompt rendering utilities for ReqVibe.
Loads and renders Jinja2 templates from the prompts directory.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel


# Pydantic models for character card validation
class Personality(BaseModel):
    tone: str
    style: str


class ExampleInteraction(BaseModel):
    user: str
    ai: str


class CharacterCard(BaseModel):
    name: str
    role: str
    expertise: List[str]
    personality: Personality
    knowledge_base: List[str]
    constraints: List[str]
    example_interaction: ExampleInteraction


def load_character_card(role: str = "analyst") -> CharacterCard:
    """
    Load and validate character card JSON from roles folder using Pydantic.
    
    Args:
        role: The role to load (default: "analyst"). Options: "analyst", "architect", "developer", "tester"
    
    Returns:
        CharacterCard: Validated character card data
    
    Raises:
        FileNotFoundError: If the role JSON file doesn't exist
        ValidationError: If the JSON doesn't match the expected structure
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to project root (from services/prompt_service.py to RequirenebtVIBE/)
    project_root = os.path.dirname(current_dir)
    character_card_path = os.path.join(project_root, "config", "roles", f"{role}.json")
    
    with open(character_card_path, 'r', encoding='utf-8') as f:
        character_data = json.load(f)
    
    # Validate using Pydantic
    character_card = CharacterCard(**character_data)
    return character_card


def load_role(role: str = "analyst") -> CharacterCard:
    """
    Load role configuration from roles folder.
    This is an alias for load_character_card() for compatibility.
    
    Args:
        role: The role to load (default: "analyst"). Options: "analyst", "architect", "developer", "tester"
    
    Returns:
        CharacterCard: Validated character card data
    """
    return load_character_card(role)


def contains_requirement_phrase(message: str) -> bool:
    """
    Check if user message contains requirement-like phrases.
    
    Args:
        message (str): User message to check
    
    Returns:
        bool: True if message contains requirement-like phrases
    """
    # Convert to lowercase for case-insensitive matching
    message_lower = message.lower()
    
    # Requirement-like phrases
    requirement_phrases = [
        # Core modal verbs & direct obligation
        r'\bmust\b',
        r'\bshall\b',
        r'\bneed\b',
        r'\bneeds\b',
        r'\bneeded\b',
        r'\bneeding\b',

        # "Require" family
        r'\brequire\b',
        r'\brequires\b',
        r'\brequired\b',
        r'\brequirement\b',
        r'\brequirements\b',
        r'\brequiring\b',

        # "Should" family (recommendation → often treated as soft requirement)
        r'\bshould\b',
        r'\bshouldn\'t\b',        # negative form
        r'\bought to\b',

        # "Have to" / necessity
        r'\bhave to\b',
        r'\bhas to\b',
        r'\bhaving to\b',
        r'\bhad to\b',

        # Desire / request
        r'\bwant\b',
        r'\bwants\b',
        r'\bwanted\b',
        r'\bwould like\b',
        r'\bwould prefer\b',
        r'\bwish\b',
        r'\bwishes\b',

        # Expectation / mandate
        r'\bexpect\b',
        r'\bexpects\b',
        r'\bexpected\b',
        r'\bmandate\b',
        r'\bmandates\b',
        r'\bmandated\b',
        r'\bmandating\b',

        # Obligation synonyms
        r'\bobligated?\b',         # matches "obligate", "obligated"
        r'\bobligation\b',
        r'\bobligations\b',
        r'\bduty\b',
        r'\bduties\b',
        r'\bresponsibility\b',
        r'\bresponsibilities\b',

        # Contractual / compliance
        r'\bwill be required\b',
        r'\bis required\b',
        r'\bare required\b',
        r'\bmust be\b',
        r'\bshall be\b',
        r'\bis mandatory\b',
        r'\bare mandatory\b',
        r'\bcompulsory\b',

        # Softer phrasing sometimes misused as requirement
        r'\bit is necessary\b',
        r'\bit is essential\b',
        r'\bit is critical\b',
        r'\bit is important\b',    # caution: very soft
        r'\bdesire\b',
        r'\bdesires\b',
        r'\bprefer\b',
        r'\bprefers\b',
        r'\bpreferred\b',
    ]
    
    # Check if any phrase matches
    for phrase in requirement_phrases:
        if re.search(phrase, message_lower):
            return True
    
    return False


def render_prompt(template_name, context_dict):
    """
    Loads a Jinja2 template from the prompts/ directory and renders it with the provided context.
    
    Args:
        template_name (str): Name of the template file (e.g., "base" for "base.jinja")
        context_dict (dict): Dictionary of variables to use when rendering the template
    
    Returns:
        str: Rendered template as a string
    
    Example:
        >>> context = {"character": {"name": "ReqVibe", "role": "Consultant"}}
        >>> prompt = render_prompt("base", context)
    """
    # Get the directory where this script is located (services/prompt_service.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up one level to project root (RequirenebtVIBE/), then into 'prompts'
    project_root = os.path.dirname(current_dir)
    templates_dir = os.path.join(project_root, "prompts")
    
    # Create Jinja2 environment with the templates directory
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Add the template extension if not present
    if not template_name.endswith('.jinja'):
        template_name = f"{template_name}.jinja"
    
    # Load the template
    template = env.get_template(template_name)
    
    # Render the template with the context
    rendered = template.render(**context_dict)
    
    return rendered


def generate_next_req_id(requirements: List[Dict[str, Any]]) -> str:
    """
    Generate the next REQ-ID based on existing requirements.
    
    Args:
        requirements: List of requirement dictionaries with 'id' key (e.g., "REQ-001")
    
    Returns:
        str: Next REQ-ID (e.g., "REQ-001", "REQ-002", etc.)
    """
    if not requirements:
        return "REQ-001"
    
    # Extract all REQ-IDs and find the maximum
    max_id = 0
    for req in requirements:
        req_id = req.get("id", "")
        if req_id.startswith("REQ-"):
            try:
                req_num = int(req_id.replace("REQ-", ""))
                max_id = max(max_id, req_num)
            except ValueError:
                continue
    
    # Generate next ID
    next_id = max_id + 1
    return f"REQ-{next_id:03d}"


def parse_volere_fields(message: str) -> Dict[str, Any]:
    """
    Parse Volere fields (goal, context, stakeholder) from a message.
    
    Args:
        message: Text message to parse
    
    Returns:
        dict: Dictionary with goal, context, stakeholder (values may be empty if not found)
    """
    fields = {
        "goal": "",
        "context": "",
        "stakeholder": ""
    }
    
    message_lower = message.lower()
    
    # Common context indicators
    context_patterns = {
        "context": [
            r'\b(web|website|web app|web application)\b',
            r'\b(mobile|android|ios|iphone|ipad)\b',
            r'\b(desktop|windows|mac|linux)\b',
            r'\b(api|rest|graphql)\b',
            r'\b(cloud|aws|azure|gcp)\b',
        ],
        "stakeholder": [
            r'\b(user|users|end user|end users)\b',
            r'\b(admin|administrator|administrators)\b',
            r'\b(developer|developers|dev)\b',
            r'\b(customer|customers|client|clients)\b',
            r'\b(manager|managers|management)\b',
        ],
        "goal": [
            r'\b(authenticate|authentication|login|sign in)\b',
            r'\b(register|registration|sign up)\b',
            r'\b(secure|security|protect|protection)\b',
            r'\b(validate|validation|verify|verification)\b',
        ]
    }
    
    # Extract context (platform/technology)
    for pattern in context_patterns["context"]:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            fields["context"] = match.group(1)
            break
    
    # Extract stakeholder
    for pattern in context_patterns["stakeholder"]:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            fields["stakeholder"] = match.group(1)
            break
    
    # Extract goal (action/purpose)
    for pattern in context_patterns["goal"]:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            fields["goal"] = match.group(1)
            break
    
    return fields


def detect_conflicts(user_message: str, requirements: List[Dict[str, Any]]) -> Optional[str]:
    """
    Detect conflicts between user message and existing requirements.
    
    Args:
        user_message: Current user message
        requirements: List of requirement dictionaries with 'volere' key containing volere fields
    
    Returns:
        Optional[str]: Conflict message if conflict detected, None otherwise
    """
    if not requirements:
        return None
    
    # Parse current message
    current_fields = parse_volere_fields(user_message)
    user_msg_lower = user_message.lower()
    
    # Conflict patterns (platform conflicts)
    platform_conflicts = [
        ("web", ["mobile", "android", "ios", "iphone", "ipad"]),
        ("mobile", ["web", "website", "web app", "desktop"]),
        ("android", ["ios", "iphone", "ipad", "web"]),
        ("ios", ["android", "web", "desktop"]),
        ("desktop", ["mobile", "android", "ios", "web"]),
    ]
    
    # Check for platform conflicts
    for platform, conflicting in platform_conflicts:
        if any(word in user_msg_lower for word in [platform]):
            # Check if any existing requirement mentions conflicting platforms
            for req in requirements:
                volere = req.get("volere", {})
                req_context = volere.get("context", "").lower()
                req_text = req.get("text", "").lower()
                
                for conflict_platform in conflicting:
                    if conflict_platform in req_context or conflict_platform in req_text:
                        # Extract the platform mentioned in the requirement
                        mentioned_platform = conflict_platform
                        # Try to find a more specific platform name
                        for word in req_text.split():
                            if any(plat in word.lower() for plat in conflicting):
                                mentioned_platform = word
                                break
                        return f"Conflict detected: earlier said '{mentioned_platform}'. Clarify?"
    
    # Check for context field conflicts
    if current_fields["context"]:
        for req in requirements:
            volere = req.get("volere", {})
            req_context = volere.get("context", "").lower()
            
            if req_context and current_fields["context"].lower() != req_context:
                # Check if they're conflicting platforms
                current_ctx = current_fields["context"].lower()
                if (current_ctx in ["web", "website", "web app", "web application"] and 
                    req_context in ["mobile", "android", "ios", "iphone", "ipad"]):
                    return f"Conflict detected: earlier said '{req_context}'. Clarify?"
                elif (current_ctx in ["mobile", "android", "ios", "iphone", "ipad"] and 
                      req_context in ["web", "website", "web app", "web application"]):
                    return f"Conflict detected: earlier said '{req_context}'. Clarify?"
    
    return None


def extract_volere_from_requirements(requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract Volere fields from stored requirements to auto-fill known fields.
    
    Args:
        requirements: List of requirement dictionaries with 'volere' key
    
    Returns:
        dict: Dictionary with goal, context, stakeholder (most common values from requirements)
    """
    if not requirements:
        return {
            "goal": "Not stated",
            "context": "Not asked",
            "stakeholder": "Unknown"
        }
    
    # Collect all volere fields from requirements
    goals = []
    contexts = []
    stakeholders = []
    
    for req in requirements:
        volere = req.get("volere", {})
        if volere.get("goal") and volere["goal"] not in ["Not stated", ""]:
            goals.append(volere["goal"])
        if volere.get("context") and volere["context"] not in ["Not asked", ""]:
            contexts.append(volere["context"])
        if volere.get("stakeholder") and volere["stakeholder"] not in ["Unknown", ""]:
            stakeholders.append(volere["stakeholder"])
    
    # Use most common value, or first if all are unique
    def most_common(values):
        if not values:
            return None
        counter = Counter(values)
        return counter.most_common(1)[0][0]
    
    return {
        "goal": most_common(goals) or "Not stated",
        "context": most_common(contexts) or "Not asked",
        "stakeholder": most_common(stakeholders) or "Unknown"
    }


def extract_volere_context(history: List[Dict[str, str]], requirements: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Extract Volere context (goal, context, stakeholder) from conversation history and stored requirements.
    
    Args:
        history: List of message dictionaries with 'role' and 'content' keys
        requirements: Optional list of stored requirements to auto-fill from
    
    Returns:
        dict: Dictionary with goal, context, stakeholder, req_id, and description
    """
    # Start with auto-filled values from stored requirements
    if requirements:
        context = extract_volere_from_requirements(requirements)
        context["req_id"] = generate_next_req_id(requirements)
    else:
        context = {
            "goal": "Not stated",
            "context": "Not asked",
            "stakeholder": "Unknown",
            "req_id": "REQ-001"
        }
    
    context["description"] = ""
    
    # Extract information from history (override auto-filled values if more recent)
    # Look for patterns in assistant messages that indicate Volere analysis
    for message in history:
        if message.get("role") == "assistant":
            content = message.get("content", "")
            
            # Try to extract goal
            goal_match = re.search(r'Goal[:\s]+([^\n]+)', content, re.IGNORECASE)
            if goal_match:
                goal_value = goal_match.group(1).strip()
                if goal_value and goal_value not in ["Not stated", ""]:
                    context["goal"] = goal_value
            
            # Try to extract context
            context_match = re.search(r'Context[:\s]+([^\n]+)', content, re.IGNORECASE)
            if context_match:
                context_value = context_match.group(1).strip()
                if context_value and context_value not in ["Not asked", ""]:
                    context["context"] = context_value
            
            # Try to extract stakeholder
            stakeholder_match = re.search(r'Stakeholder[:\s]+([^\n]+)', content, re.IGNORECASE)
            if stakeholder_match:
                stakeholder_value = stakeholder_match.group(1).strip()
                if stakeholder_value and stakeholder_value not in ["Unknown", ""]:
                    context["stakeholder"] = stakeholder_value
    
    return context


def decide_and_build_prompt(
    user_message: str, 
    history: List[Dict[str, str]], 
    requirements: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, str]], Optional[str], Optional[Dict[str, Any]]]:
    """
    Decide which template to use based on user message and build the full prompt.
    
    Args:
        user_message (str): The current user message
        history (List[Dict[str, str]]): Conversation history as list of message dicts
                                        with 'role' and 'content' keys
        requirements (Optional[List[Dict[str, Any]]]): List of stored requirements with 
                                                       'id', 'text', 'volere' keys
    
    Returns:
        tuple: (messages_list, conflict_message, new_requirement_data)
            - messages_list: Full messages list ready for API call
            - conflict_message: Conflict detection message if conflict found, None otherwise
            - new_requirement_data: Dict with 'id', 'text', 'volere' for new requirement if detected, None otherwise
    """
    # Load character card - use role from session state if available, otherwise default to "analyst"
    try:
        import streamlit as st
        selected_role = st.session_state.get("selected_role", "analyst")
    except (ImportError, RuntimeError):
        # If streamlit is not available (e.g., during testing), use default role
        selected_role = "analyst"
    character_card = load_character_card(role=selected_role)
    
    # Store role data in session state for quick access
    try:
        st.session_state.role_data = character_card.model_dump()
    except (NameError, RuntimeError):
        # If streamlit is not available, skip storing in session state
        pass
    
    # Convert character card to dict for template rendering
    character_dict = character_card.model_dump()
    
    # Initialize return values
    conflict_message = None
    new_requirement_data = None
    
    # Check if user message contains requirement-like phrases
    if contains_requirement_phrase(user_message):
        # Detect conflicts
        if requirements:
            conflict_message = detect_conflicts(user_message, requirements)
        
        # Use volere.jinja template with context from history and requirements
        volere_context = extract_volere_context(history, requirements)
        
        # Parse volere fields from current message to supplement context
        parsed_fields = parse_volere_fields(user_message)
        
        # Update context with parsed fields if they're not already set
        if parsed_fields["goal"] and volere_context["goal"] == "Not stated":
            volere_context["goal"] = parsed_fields["goal"]
        if parsed_fields["context"] and volere_context["context"] == "Not asked":
            volere_context["context"] = parsed_fields["context"]
        if parsed_fields["stakeholder"] and volere_context["stakeholder"] == "Unknown":
            volere_context["stakeholder"] = parsed_fields["stakeholder"]
        
        # Update description with current user message
        if user_message.strip():
            volere_context["description"] = user_message.strip()
        
        # Prepare new requirement data
        new_requirement_data = {
            "id": volere_context["req_id"],
            "text": user_message.strip(),
            "volere": {
                "goal": volere_context["goal"],
                "context": volere_context["context"],
                "stakeholder": volere_context["stakeholder"]
            }
        }
        
        # Merge character data with volere context
        template_context = {
            "character": character_dict,
            **volere_context
        }
        system_prompt = render_prompt("volere", template_context)
        
        # Also include base character prompt for context
        base_prompt = render_prompt("base", {"character": character_dict})
        
        # Add conflict message to system prompt if conflict detected
        if conflict_message:
            system_prompt = f"{base_prompt}\n\n{system_prompt}\n\n⚠️ {conflict_message}"
        else:
            system_prompt = f"{base_prompt}\n\n{system_prompt}"
    else:
        # Use base.jinja template
        template_context = {
            "character": character_dict
        }
        system_prompt = render_prompt("base", template_context)
    
    # Enhance prompt with Mermaid diagram instructions if needed
    from utils.mermaid_renderer import enhance_prompt_for_mermaid
    system_prompt = enhance_prompt_for_mermaid(user_message, system_prompt)
    
    # Build the full messages list
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add history
    messages.extend(history)
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages, conflict_message, new_requirement_data
