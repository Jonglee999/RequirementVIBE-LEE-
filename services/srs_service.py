"""
SRS Generation Service

This module provides functionality for generating IEEE 830 Software Requirements
Specification documents from conversation history.
"""

import streamlit as st
from typing import List, Dict, Any


def generate_ieee830_srs_from_conversation(client, assistant_messages: List[str], model: str = None) -> str:
    """
    Generate IEEE 830 SRS document from conversation history using LLM API.
    
    This function takes all assistant messages from a conversation and uses an LLM
    to analyze and format them into a complete IEEE 830 Software Requirements
    Specification document. The LLM extracts requirements, organizes them by category,
    and structures them according to IEEE 830 standards.
    
    Process:
    1. Combines all assistant messages into a formatted context string
    2. Creates a system prompt instructing the LLM to generate IEEE 830 SRS
    3. Sends the context and instructions to the LLM API
    4. Returns the generated Markdown document
    
    Args:
        client: Initialized API client (CentralizedLLMClient or OpenAI-compatible)
        assistant_messages: List of assistant message content strings from the conversation
    
    Returns:
        str: Complete IEEE 830 SRS document in Markdown format, including:
            - Introduction (Purpose, Scope, Definitions, References, Overview)
            - Overall Description (Product Perspective, Functions, User Characteristics)
            - Specific Requirements (Functional, Non-Functional, Interface, Performance)
    
    Note:
        Only assistant messages are used (not user messages) to focus on the
        requirements that were identified and analyzed by the AI.
    """
    # Handle empty conversation case - return template with instructions
    if not assistant_messages:
        return "# Software Requirements Specification (IEEE 830)\n\n## 1. Introduction\n\nNo requirements have been captured yet. Please start a conversation with the AI assistant to analyze and capture requirements."
    
    # Combine all assistant messages into a single formatted context string
    # Each message is numbered and separated by dividers for clarity
    # This context is sent to the LLM for analysis and formatting
    conversation_context = "\n\n---\n\n".join([
        f"**Assistant Response {i+1}:**\n{msg}" 
        for i, msg in enumerate(assistant_messages)
    ])
    
    # Create system prompt that instructs the LLM on how to generate the SRS
    # The prompt specifies the IEEE 830 structure and what information to extract
    system_prompt = """You are a professional requirements engineer. Your task is to analyze the conversation history (specifically the assistant's responses) and generate a complete Software Requirements Specification (SRS) document following the IEEE 830 standard format.

The IEEE 830 SRS structure should include:
1. Introduction
   1.1 Purpose
   1.2 Scope
   1.3 Definitions, Acronyms, and Abbreviations
   1.4 References
   1.5 Overview
2. Overall Description
   2.1 Product Perspective
   2.2 Product Functions
   2.3 User Characteristics
   2.4 Constraints
   2.5 Assumptions and Dependencies
3. Specific Requirements
   3.1 Functional Requirements
   3.2 Non-Functional Requirements
   3.3 Interface Requirements
   3.4 Performance Requirements
   3.5 Design Constraints

Extract all requirements mentioned in the assistant responses. For each requirement, include:
- Requirement ID (REQ-XXX format if available)
- Requirement description
- Priority (if mentioned)
- Dependencies (if mentioned)
- Acceptance criteria (if mentioned)

Format the output as a well-structured Markdown document following IEEE 830 standards. Be comprehensive and organized."""

    # Create user prompt that includes the conversation context and specific instructions
    user_prompt = f"""Please analyze the following assistant responses from a requirements engineering conversation and generate a complete IEEE 830 SRS document in Markdown format.

**Conversation History (Assistant Responses Only):**

{conversation_context}

**Instructions:**
- Extract all requirements, functional and non-functional
- Organize them according to IEEE 830 SRS structure
- Include all requirement IDs (REQ-XXX) if present
- Include Volere fields (Goal, Context, Stakeholder) if mentioned
- Be comprehensive and well-structured
- Use proper Markdown formatting with headers, lists, and tables where appropriate

Generate the complete SRS document now:"""
    
    try:
        # Get model from parameter or session state
        if model is None:
            model = st.session_state.get("selected_model", "deepseek-chat")
        
        # Call the LLM API to generate the SRS document
        # Uses the currently selected model (can be DeepSeek, GPT, Claude, or Grok)
        # Note: SRS generation can take longer due to large output, so we use extended timeout
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},  # Instructions for SRS structure
                {"role": "user", "content": user_prompt}       # Conversation context + formatting instructions
            ],
            temperature=0.3,   # Lower temperature for more consistent, structured output (less creative variation)
            max_tokens=12000,  # Allow for comprehensive SRS document (may need adjustment for very long documents)
            timeout=180        # Extended timeout (3 minutes) for large document generation
        )
        
        # Extract the generated SRS content from the API response
        srs_content = response.choices[0].message.content
        
        # Ensure the document starts with a proper Markdown header
        # Some models may omit the main header, so we add it if missing
        if not srs_content.startswith("#"):
            srs_content = "# Software Requirements Specification (IEEE 830)\n\n" + srs_content
        
        return srs_content
    except Exception as e:
        # Re-raise with more context about what operation failed
        raise Exception(f"Failed to generate SRS from API: {str(e)}")

