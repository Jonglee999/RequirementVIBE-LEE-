"""
Requirement Extraction Service for ReqVibe

This module handles extraction of requirements from AI responses.
It uses regex patterns to identify REQ-XXX IDs and extract associated requirement text.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def extract_requirements_from_response(
    ai_response: str,
    existing_requirements: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Extract requirements from AI response by finding REQ-XXX patterns.
    
    This function:
    1. Searches for REQ-XXX patterns in the AI response
    2. Extracts requirement text associated with each REQ-ID
    3. Extracts Volere fields (goal, context, stakeholder) if available
    4. Generates unique REQ-IDs if duplicates are found
    5. Returns a list of requirement dictionaries
    
    Args:
        ai_response: The AI assistant's response text
        existing_requirements: Optional list of existing requirements to check for duplicates
    
    Returns:
        List[Dict[str, Any]]: List of requirement dictionaries with:
            - id: REQ-ID (e.g., "REQ-001")
            - text: Requirement text extracted from response
            - volere: Dictionary with goal, context, stakeholder fields
    """
    if not ai_response:
        return []
    
    existing_requirements = existing_requirements or []
    
    # Pattern to match REQ-XXX IDs (e.g., REQ-001, REQ-123)
    req_pattern = r'REQ-\d{3,}'
    found_req_ids = re.findall(req_pattern, ai_response, re.IGNORECASE)
    
    if not found_req_ids:
        return []
    
    # Get unique requirement IDs (normalized to uppercase)
    unique_req_ids = list(set([req_id.upper() for req_id in found_req_ids]))
    
    # Get existing REQ-IDs to check for duplicates
    existing_req_ids = {req.get("id", "").upper() for req in existing_requirements}
    
    # Calculate maximum REQ-ID number from existing requirements
    max_req_id = 0
    for req in existing_requirements:
        req_id = req.get("id", "")
        if req_id and req_id.upper().startswith("REQ-"):
            try:
                req_num = int(req_id.replace("REQ-", "").replace("req-", "").replace("Req-", ""))
                max_req_id = max(max_req_id, req_num)
            except ValueError:
                continue
    
    extracted_requirements = []
    
    # Extract requirement data for each REQ-ID found
    for original_req_id in unique_req_ids:
        # Check if this REQ-ID already exists
        # If it exists, generate a new unique ID to avoid conflicts
        req_id = original_req_id
        if original_req_id in existing_req_ids:
            max_req_id += 1
            req_id = f"REQ-{max_req_id:03d}"
            print(f"DEBUG: REQ-ID {original_req_id} already exists, using new ID: {req_id}")
        
        # Try to extract requirement text using multiple patterns
        req_text = _extract_requirement_text(ai_response, original_req_id)
        
        # Only create requirement if we found requirement text
        if not req_text:
            print(f"DEBUG: Skipping {req_id} - no requirement text extracted")
            continue
        
        # Extract Volere fields from AI response
        volere = _extract_volere_fields(ai_response)
        
        # Create requirement dictionary
        requirement_data = {
            "id": req_id,
            "text": req_text,
            "volere": volere
        }
        
        extracted_requirements.append(requirement_data)
        
        # Update max_req_id for next requirement
        if req_id != original_req_id:
            try:
                req_num = int(req_id.replace("REQ-", "").replace("req-", "").replace("Req-", ""))
                max_req_id = max(max_req_id, req_num)
            except ValueError:
                pass
    
    return extracted_requirements


def _extract_requirement_text(ai_response: str, req_id: str) -> str:
    """
    Extract requirement text associated with a REQ-ID from AI response.
    
    This function tries multiple patterns to extract requirement text:
    1. Simple format: REQ-001: text directly after colon
    2. Description format: REQ-001: Title\nDescription: text
    3. Multi-line format: REQ-001: text spanning multiple lines
    4. Fallback: First line after REQ-ID
    
    Args:
        ai_response: The AI assistant's response text
        req_id: The REQ-ID to extract text for (e.g., "REQ-001")
    
    Returns:
        str: Extracted requirement text, or empty string if not found
    """
    req_text = ""
    
    # Pattern 1: Simple format - REQ-001: [text directly after colon]
    simple_patterns = [
        # Pattern 1a: REQ-001: text (stops at newline with number or section header)
        rf'{re.escape(req_id)}[:\-\s]+([^\n]+?)(?:\n\s*(?:\d+\.|REQ-|Goal|Context|Stakeholder|Rationale|Description|Clarifying|Generated|Acknowledge)|$)',
        # Pattern 1b: REQ-001: text (stops at end of line or next section)
        rf'{re.escape(req_id)}[:\-\s]+([^\n]+)',
        # Pattern 1c: REQ-001: text (multi-line until next numbered section)
        rf'{re.escape(req_id)}[:\-\s]+([^\n]+(?:\n(?!\d+\.|REQ-|Goal|Context|Stakeholder|Rationale|Description|Clarifying|Generated|Acknowledge)[^\n]+)*)'
    ]
    
    for simple_pattern in simple_patterns:
        simple_match = re.search(simple_pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if simple_match:
            req_text = simple_match.group(1).strip()
            # Clean up: remove markdown formatting
            req_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', req_text)  # Remove bold
            req_text = re.sub(r'`([^`]+)`', r'\1', req_text)  # Remove code blocks
            req_text = re.sub(r'^\s*:\s*', '', req_text)  # Remove leading colon if any
            req_text = re.sub(r'\.\s*$', '', req_text)  # Remove trailing periods
            if req_text:
                print(f"DEBUG: Extracted requirement text for {req_id} using simple pattern: {req_text[:100]}...")
                break
    
    # Pattern 2: Look for "Description:" section after REQ-ID
    if not req_text:
        desc_patterns = [
            # Pattern 2a: REQ-001: Title\nDescription: text
            rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n[^\n]*)*?\n\s*\*\*?Description\*\*?[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)',
            # Pattern 2b: REQ-001: Title\n**Description:** text
            rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n[^\n]*)*?\n.*?Description[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)',
            # Pattern 2c: Simple Description: text after REQ-ID
            rf'{re.escape(req_id)}[:\-\s]*[^\n]*(?:\n.*?)?Description[:\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description)[^\n]+)*)'
        ]
        for desc_pattern in desc_patterns:
            desc_match = re.search(desc_pattern, ai_response, re.IGNORECASE | re.DOTALL)
            if desc_match:
                req_text = desc_match.group(1).strip()
                print(f"DEBUG: Extracted requirement text for {req_id} using Description pattern: {req_text[:100]}...")
                break
    
    # Pattern 3: Multi-line text after REQ-ID until next section
    if not req_text:
        pattern = rf'{re.escape(req_id)}[:\-\s]+([^\n]+(?:\n(?!\*\*|REQ-|Goal|Context|Stakeholder|Rationale|Description|\d+\.)[^\n]+)*)'
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            req_text = match.group(1).strip()
            # Clean up: remove markdown formatting and limit to reasonable length
            req_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', req_text)  # Remove bold
            req_text = re.sub(r'`([^`]+)`', r'\1', req_text)  # Remove code blocks
            # Take first 500 characters or until next major section
            if len(req_text) > 500:
                req_text = req_text[:500].rsplit('\n', 1)[0]
            print(f"DEBUG: Extracted requirement text for {req_id} using multi-line pattern: {req_text[:100]}...")
    
    # Pattern 4: Fallback - just get the first line after REQ-ID
    if not req_text:
        pattern = rf'{re.escape(req_id)}[:\-\s]+([^\n]+)'
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            req_text = match.group(1).strip()
            # Clean up markdown
            req_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', req_text)
            req_text = re.sub(r'`([^`]+)`', r'\1', req_text)
            print(f"DEBUG: Extracted requirement text for {req_id} using fallback pattern: {req_text[:100]}...")
    
    return req_text


def _extract_volere_fields(ai_response: str) -> Dict[str, str]:
    """
    Extract Volere fields (goal, context, stakeholder) from AI response.
    
    Args:
        ai_response: The AI assistant's response text
    
    Returns:
        Dict[str, str]: Dictionary with goal, context, stakeholder fields
    """
    volere = {
        "goal": "Not stated",
        "context": "Not asked",
        "stakeholder": "Unknown"
    }
    
    # Try to extract goal
    goal_match = re.search(r'Goal[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
    if goal_match:
        goal_value = goal_match.group(1).strip()
        if goal_value and goal_value not in ["Not stated", ""]:
            volere["goal"] = goal_value
    
    # Try to extract context
    context_match = re.search(r'Context[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
    if context_match:
        context_value = context_match.group(1).strip()
        if context_value and context_value not in ["Not asked", ""]:
            volere["context"] = context_value
    
    # Try to extract stakeholder
    stakeholder_match = re.search(r'Stakeholder[:\s]+([^\n]+)', ai_response, re.IGNORECASE)
    if stakeholder_match:
        stakeholder_value = stakeholder_match.group(1).strip()
        if stakeholder_value and stakeholder_value not in ["Unknown", ""]:
            volere["stakeholder"] = stakeholder_value
    
    return volere


def merge_requirement_with_pending(
    requirement: Dict[str, Any],
    pending_requirement: Optional[Dict[str, Any]],
    original_req_id: str
) -> Dict[str, Any]:
    """
    Merge requirement extracted from AI response with pending requirement data.
    
    This function merges Volere fields from a pending requirement (user-provided)
    with a requirement extracted from the AI response. AI response takes precedence,
    but missing fields are filled in from the pending requirement.
    
    Args:
        requirement: Requirement dictionary extracted from AI response
        pending_requirement: Optional pending requirement dictionary from user input
        original_req_id: Original REQ-ID from AI response (before uniqueness check)
    
    Returns:
        Dict[str, Any]: Merged requirement dictionary
    """
    if not pending_requirement:
        return requirement
    
    # Check if pending requirement matches the original REQ-ID
    pending_req_id = pending_requirement.get("id", "").upper()
    if pending_req_id != original_req_id:
        return requirement
    
    # Merge volere fields (AI response takes precedence, but fill in missing fields)
    volere = requirement.get("volere", {})
    pending_volere = pending_requirement.get("volere", {})
    
    for key in ["goal", "context", "stakeholder"]:
        if key not in volere or volere[key] in ["Not stated", "Not asked", "Unknown"]:
            if key in pending_volere and pending_volere[key] not in ["Not stated", "Not asked", "Unknown"]:
                volere[key] = pending_volere[key]
    
    requirement["volere"] = volere
    return requirement

