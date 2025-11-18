"""
Tool Service for ReqVibe

This module handles tool calls based on role-specific triggers.
Tools include Mermaid diagram generation, Gherkin test case generation, etc.
"""

import re
from typing import Optional, Dict, Any, List


def check_tool_triggers(user_message: str, tool_config: Dict[str, Any]) -> bool:
    """
    Check if user message triggers any tool based on tool configuration.
    
    Args:
        user_message: User's input message
        tool_config: Tool configuration dictionary with trigger_keywords
        
    Returns:
        True if any trigger keyword is found, False otherwise
    """
    if not tool_config or "trigger_keywords" not in tool_config:
        return False
    
    user_lower = user_message.lower()
    trigger_keywords = tool_config.get("trigger_keywords", [])
    
    for keyword in trigger_keywords:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, user_lower, re.IGNORECASE):
            return True
    
    return False


def generate_mermaid_diagram_prompt(user_message: str, context: str = "") -> str:
    """
    Generate a prompt enhancement to encourage Mermaid diagram generation.
    
    Args:
        user_message: User's input message
        context: Additional context for the diagram
        
    Returns:
        Enhanced prompt string for Mermaid diagram generation
    """
    mermaid_instruction = """
IMPORTANT: The user's message indicates they want an architecture or design diagram.
You MUST include a Mermaid diagram in your response. Format it as:

```mermaid
[your mermaid diagram code here]
```

Recommended diagram types:
- Architecture Diagram: Use "flowchart TD" or "graph TD" to show system components and relationships
- System Design: Use "flowchart LR" for horizontal flow, "flowchart TD" for top-down hierarchy
- Sequence Diagram: Use "sequenceDiagram" for interaction flows
- Component Diagram: Use "flowchart" with clear component separation

Make sure the diagram accurately represents the requested architecture or design.
Include labels, relationships, and key components clearly.
"""
    
    return mermaid_instruction


def generate_gherkin_prompt(user_message: str, context: str = "") -> str:
    """
    Generate a prompt enhancement to encourage Gherkin test case generation.
    
    Args:
        user_message: User's input message
        context: Additional context for the test cases
        
    Returns:
        Enhanced prompt string for Gherkin test case generation
    """
    gherkin_instruction = """
IMPORTANT: The user's message indicates they want test cases or test scenarios.
You MUST include Gherkin (BDD) format test cases in your response. Format it as:

```gherkin
Feature: [Feature Name]
  Scenario: [Scenario Name]
    Given [precondition]
    When [action]
    Then [expected outcome]
    
  Scenario Outline: [Scenario Name with Examples]
    Given [precondition with <variable>]
    When [action with <variable>]
    Then [expected outcome with <variable>]
    
    Examples:
      | variable | value1 | value2 |
      | var1     | val1   | val2   |
```

Gherkin Best Practices:
- Use clear, business-readable language
- Each scenario should be independent and testable
- Include both happy path and edge cases
- Use Background for common setup steps
- Use Scenario Outline for data-driven tests
- Link test cases to requirement IDs when applicable (e.g., REQ-FUNC-001)

Make sure the test cases are:
- Clear and understandable by non-technical stakeholders
- Traceable to requirements
- Cover positive, negative, and boundary cases
"""
    
    return gherkin_instruction


def call_tool(tool_action: str, user_message: str, context: str = "") -> Optional[str]:
    """
    Call a specific tool based on action type.
    
    Args:
        tool_action: The action to perform (e.g., "generate_mermaid_diagram", "generate_gherkin")
        user_message: User's input message
        context: Additional context
        
    Returns:
        Enhanced prompt string if tool is called, None otherwise
    """
    if tool_action == "generate_mermaid_diagram":
        return generate_mermaid_diagram_prompt(user_message, context)
    elif tool_action == "generate_gherkin":
        return generate_gherkin_prompt(user_message, context)
    elif tool_action == "generate_test_plan":
        # Map generate_test_plan to generate_gherkin for tester role
        return generate_gherkin_prompt(user_message, context)
    else:
        # Unknown tool action
        return None

