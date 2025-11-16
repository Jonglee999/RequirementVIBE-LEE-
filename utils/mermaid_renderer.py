"""
Mermaid Diagram Renderer for Streamlit

This module provides functionality to detect, extract, and render Mermaid diagrams
in Streamlit chat messages. It includes:
- Mermaid code detection and extraction
- HTML/JavaScript-based diagram rendering
- Fallback to code display if rendering fails
"""

import re
import streamlit as st
from typing import List, Tuple, Optional


def extract_mermaid_code(text: str) -> List[Tuple[str, int, int]]:
    """
    Extract Mermaid code blocks from text.
    
    Args:
        text: Input text that may contain Mermaid code blocks
        
    Returns:
        List of tuples (mermaid_code, start_pos, end_pos) for each found block
    """
    mermaid_blocks = []
    
    # Pattern 1: ```mermaid ... ``` (most common)
    pattern1 = r'```\s*mermaid\s*\n(.*?)```'
    for match in re.finditer(pattern1, text, re.DOTALL | re.IGNORECASE):
        code = match.group(1).strip()
        # Clean up the code - remove any leading/trailing whitespace and backticks
        code = re.sub(r'^```+\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'```+\s*$', '', code, flags=re.MULTILINE)
        code = code.strip()
        if code and any(keyword in code.lower() for keyword in ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram', 'erDiagram', 'gantt', 'pie']):
            mermaid_blocks.append((code, match.start(), match.end()))
    
    # Pattern 2: ``` ... ``` with mermaid syntax inside (but no mermaid label)
    # Only if Pattern 1 didn't catch it
    if not mermaid_blocks:
        pattern2 = r'```\s*\n((?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie).*?)```'
        for match in re.finditer(pattern2, text, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            # Clean up the code
            code = re.sub(r'^```+\s*', '', code, flags=re.MULTILINE)
            code = re.sub(r'```+\s*$', '', code, flags=re.MULTILINE)
            code = code.strip()
            if code:
                mermaid_blocks.append((code, match.start(), match.end()))
    
    # Pattern 3: Direct mermaid syntax without code blocks (only if no code blocks found)
    if not mermaid_blocks:
        mermaid_keywords = [
            r'^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie)',
        ]
        for keyword_pattern in mermaid_keywords:
            for match in re.finditer(keyword_pattern, text, re.MULTILINE | re.IGNORECASE):
                # Try to extract the full diagram (until next empty line or end)
                end_pos = match.end()
                # Find the end of the diagram (next double newline or end of text)
                next_double_newline = text.find('\n\n', end_pos)
                if next_double_newline != -1:
                    diagram_text = text[match.start():next_double_newline].strip()
                else:
                    diagram_text = text[match.start():].strip()
                
                if diagram_text and len(diagram_text) > 10:  # Minimum length check
                    mermaid_blocks.append((diagram_text, match.start(), match.start() + len(diagram_text)))
                break  # Only take the first match
    
    return mermaid_blocks


# Track if Mermaid.js has been loaded
_mermaid_initialized = False


def _get_mermaid_init_script() -> str:
    """Get the Mermaid.js initialization script (only once per page)."""
    return """
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        (function() {
            // Only initialize once
            if (window.mermaidInitialized) return;
            window.mermaidInitialized = true;
            
            // Wait for Mermaid to load
            if (typeof mermaid === 'undefined') {
                // Retry after a short delay
                setTimeout(function() {
                    if (typeof mermaid !== 'undefined') {
                        _initializeMermaid();
                    }
                }, 100);
                return;
            }
            
            _initializeMermaid();
            
            function _initializeMermaid() {
                if (typeof mermaid === 'undefined') {
                    console.error('Mermaid library failed to load');
                    return;
                }
                
                // Configure Mermaid
                mermaid.initialize({
                    startOnLoad: false,  // We'll render manually
                    theme: 'dark',
                    themeVariables: {
                        primaryColor: '#10a37f',
                        primaryTextColor: '#ececf1',
                        primaryBorderColor: '#565869',
                        lineColor: '#8e8ea0',
                        secondaryColor: '#343541',
                        tertiaryColor: '#202123',
                        background: '#1e1e1e',
                        mainBkg: '#1e1e1e',
                        secondBkg: '#343541',
                        textColor: '#ececf1',
                        border1: '#565869',
                        border2: '#8e8ea0',
                        arrowheadColor: '#10a37f',
                        fontSize: '16px'
                    },
                    flowchart: {
                        useMaxWidth: true,
                        htmlLabels: true,
                        curve: 'basis'
                    },
                    sequence: {
                        diagramMarginX: 50,
                        diagramMarginY: 10,
                        actorMargin: 50,
                        width: 150,
                        height: 65,
                        boxMargin: 10,
                        boxTextMargin: 5,
                        noteMargin: 10,
                        messageMargin: 35,
                        mirrorActors: true,
                        bottomMarginAdj: 1,
                        useMaxWidth: true,
                        rightAngles: false,
                        showSequenceNumbers: false
                    },
                    gantt: {
                        titleTopMargin: 25,
                        barHeight: 20,
                        barGap: 4,
                        topPadding: 50,
                        leftPadding: 75,
                        gridLineStartPadding: 35,
                        fontSize: 11,
                        fontFamily: '"Open-Sans", "sans-serif"',
                        numberSectionStyles: 4,
                        axisFormat: '%Y-%m-%d',
                        topAxis: false
                    }
                });
            }
        })();
    </script>
    """


def render_mermaid_diagram(mermaid_code: str, diagram_id: Optional[str] = None) -> bool:
    """
    Render a Mermaid diagram using HTML/JavaScript via Streamlit components.
    
    Args:
        mermaid_code: Mermaid diagram code
        diagram_id: Optional unique ID for the diagram (for multiple diagrams)
        
    Returns:
        True if rendering was successful, False otherwise
    """
    if not mermaid_code or not mermaid_code.strip():
        return False
    
    try:
        # Generate unique ID if not provided
        if diagram_id is None:
            import hashlib
            diagram_id = f"mermaid_{hashlib.md5(mermaid_code.encode()).hexdigest()[:8]}"
        
        # Escape HTML special characters in the code for fallback display
        escaped_code = mermaid_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
        
        # Use Streamlit components for proper JavaScript execution
        import streamlit.components.v1 as components
        
        # Create complete HTML with Mermaid.js
        mermaid_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #1e1e1e;
                }}
                .mermaid-container {{
                    margin: 0.5rem 0;
                    padding: 0.75rem;
                    background-color: #1e1e1e;
                    border-radius: 8px;
                    border: 1px solid #565869;
                    min-height: 200px;
                    width: 100%;
                    box-sizing: border-box;
                    overflow: visible;
                }}
                .mermaid {{
                    text-align: center;
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    min-height: 100%;
                    width: 100%;
                    margin: 0;
                    padding: 0;
                }}
                .mermaid svg {{
                    max-width: 100%;
                    height: auto;
                    overflow: visible;
                    margin: 0;
                }}
                body {{
                    overflow: visible;
                    min-height: 100%;
                }}
                .error-message {{
                    color: #ff6b6b;
                    padding: 0.5rem;
                    margin-bottom: 0.5rem;
                }}
                pre {{
                    background: #2d2d2d;
                    padding: 1rem;
                    border-radius: 4px;
                    overflow-x: auto;
                    color: #ececf1;
                    font-size: 0.9rem;
                    margin: 0;
                }}
            </style>
        </head>
        <body>
            <div class="mermaid-container">
                <div id="{diagram_id}" class="mermaid">
                    {mermaid_code}
                </div>
            </div>
            
            <script>
                (function() {{
                    function initializeMermaid() {{
                        if (typeof mermaid === 'undefined') {{
                            setTimeout(initializeMermaid, 100);
                            return;
                        }}
                        
                        // Configure Mermaid
                        mermaid.initialize({{
                            startOnLoad: false,
                            theme: 'dark',
                            themeVariables: {{
                                primaryColor: '#10a37f',
                                primaryTextColor: '#ececf1',
                                primaryBorderColor: '#565869',
                                lineColor: '#8e8ea0',
                                secondaryColor: '#343541',
                                tertiaryColor: '#202123',
                                background: '#1e1e1e',
                                mainBkg: '#1e1e1e',
                                secondBkg: '#343541',
                                textColor: '#ececf1',
                                border1: '#565869',
                                border2: '#8e8ea0',
                                arrowheadColor: '#10a37f',
                                fontSize: '16px'
                            }},
                            flowchart: {{
                                useMaxWidth: true,
                                htmlLabels: true,
                                curve: 'basis',
                                padding: 10
                            }},
                            sequence: {{
                                diagramMarginX: 20,
                                diagramMarginY: 5,
                                actorMargin: 30,
                                width: 150,
                                height: 65,
                                boxMargin: 8,
                                boxTextMargin: 4,
                                noteMargin: 8,
                                messageMargin: 25,
                                mirrorActors: true,
                                bottomMarginAdj: 1,
                                useMaxWidth: true,
                                rightAngles: false,
                                showSequenceNumbers: false
                            }},
                            gantt: {{
                                titleTopMargin: 25,
                                barHeight: 20,
                                barGap: 4,
                                topPadding: 50,
                                leftPadding: 75,
                                gridLineStartPadding: 35,
                                fontSize: 11,
                                fontFamily: '"Open-Sans", "sans-serif"',
                                numberSectionStyles: 4,
                                axisFormat: '%Y-%m-%d',
                                topAxis: false
                            }}
                        }});
                        
                        renderDiagram();
                    }}
                    
                    function renderDiagram() {{
                        if (typeof mermaid === 'undefined') {{
                            setTimeout(renderDiagram, 100);
                            return;
                        }}
                        
                        try {{
                            const element = document.getElementById('{diagram_id}');
                            if (element && !element.dataset.rendered) {{
                                element.dataset.rendered = 'true';
                                
                                mermaid.run({{
                                    nodes: [element],
                                    suppressErrors: false
                                }}).then(function() {{
                                    console.log('Mermaid diagram {diagram_id} rendered successfully');
                                }}).catch(function(error) {{
                                    console.error('Mermaid rendering error:', error);
                                    // Show error message and fallback to code
                                    element.innerHTML = '<div class="error-message">⚠️ Error rendering diagram. Showing code instead.</div><pre><code>{escaped_code}</code></pre>';
                                }});
                            }}
                        }} catch (error) {{
                            console.error('Error rendering Mermaid diagram:', error);
                            const element = document.getElementById('{diagram_id}');
                            if (element) {{
                                element.innerHTML = '<pre><code>{escaped_code}</code></pre>';
                            }}
                        }}
                    }}
                    
                    // Start initialization
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', initializeMermaid);
                    }} else {{
                        initializeMermaid();
                    }}
                }})();
            </script>
        </body>
        </html>
        """
        
        # Use components.html for proper JavaScript execution
        # Calculate approximate height based on diagram complexity
        # More generous estimate to prevent truncation: ~60px per line, minimum 400px, maximum 1200px
        lines = mermaid_code.count('\n') + 1
        # Count nodes/connections for better estimation
        node_count = mermaid_code.count('[') + mermaid_code.count('{') + mermaid_code.count('(')
        connection_count = mermaid_code.count('-->') + mermaid_code.count('---')
        # Estimate: base height + height per line + height per node/connection
        estimated_height = min(max(400, 200 + lines * 50 + (node_count + connection_count) * 15), 1200)
        components.html(mermaid_html, height=estimated_height, scrolling=True)
        return True
        
    except Exception as e:
        print(f"Error rendering Mermaid diagram: {str(e)}")
        # Fallback to code display
        st.code(mermaid_code, language="mermaid")
        return False


def render_message_with_mermaid(content: str) -> None:
    """
    Render a message content, detecting and rendering Mermaid diagrams.
    
    This function:
    1. Extracts Mermaid code blocks from the content
    2. Renders each diagram
    3. Displays the remaining text as markdown (with Mermaid blocks removed)
    4. Falls back to code display if diagram rendering fails
    
    Args:
        content: Message content that may contain Mermaid diagrams
    """
    # Extract Mermaid code blocks
    mermaid_blocks = extract_mermaid_code(content)
    
    if not mermaid_blocks:
        # No Mermaid code found, just render as markdown
        st.markdown(content)
        return
    
    # Remove Mermaid code blocks from content to prevent duplicate rendering
    # Build new content without the Mermaid blocks
    parts = []
    last_pos = 0
    
    for mermaid_code, start_pos, end_pos in mermaid_blocks:
        # Add text before this Mermaid block
        if start_pos > last_pos:
            parts.append(content[last_pos:start_pos])
        # Skip the Mermaid block (don't add it to parts)
        last_pos = end_pos
    
    # Add remaining text after last Mermaid block
    if last_pos < len(content):
        parts.append(content[last_pos:])
    
    # Render text content (without Mermaid blocks) as markdown
    text_content = ''.join(parts).strip()
    if text_content:
        st.markdown(text_content)
    
    # Render each Mermaid diagram separately
    diagram_index = 0
    for mermaid_code, start_pos, end_pos in mermaid_blocks:
        # Clean the code one more time to ensure no backticks
        clean_code = mermaid_code.strip()
        clean_code = re.sub(r'^```+\s*mermaid\s*\n?', '', clean_code, flags=re.IGNORECASE | re.MULTILINE)
        clean_code = re.sub(r'\n?```+\s*$', '', clean_code, flags=re.MULTILINE)
        clean_code = clean_code.strip()
        
        if clean_code:
            # Try to render the diagram
            diagram_id = f"mermaid_diagram_{diagram_index}"
            success = render_mermaid_diagram(clean_code, diagram_id)
            
            if not success:
                # Fallback: display as code block
                st.code(clean_code, language="mermaid")
            
            diagram_index += 1


def should_generate_mermaid(user_input: str) -> bool:
    """
    Determine if the user's input suggests they want a Mermaid diagram.
    
    Scenario 1: Explicit requests for flowcharts, activity diagrams, state machine diagrams, or model diagrams
    Scenario 2: SysML diagram requests (optional, model decides)
    
    Args:
        user_input: User's input message
        
    Returns:
        True if diagram generation is strongly suggested (Scenario 1), False otherwise
    """
    user_lower = user_input.lower()
    
    # Scenario 1: Explicit diagram requests (MUST generate)
    explicit_keywords = [
        'flowchart', 'flow chart', 'flow diagram',
        'activity diagram', 'activity chart',
        'state machine', 'state diagram', 'state chart', 'statechart',
        'model diagram', 'draw diagram', 'create diagram', 'generate diagram',
        'visual diagram', 'diagram please', 'show diagram', 'display diagram'
    ]
    
    for keyword in explicit_keywords:
        if keyword in user_lower:
            return True
    
    # Scenario 2: SysML-related (optional - model decides)
    # We don't force it here, but the prompt will encourage it
    sysml_keywords = ['sysml', 'system model', 'system diagram']
    
    return False  # For Scenario 2, let the model decide


def enhance_prompt_for_mermaid(user_input: str, base_prompt: str) -> str:
    """
    Enhance the system prompt to encourage Mermaid diagram generation when appropriate.
    
    Args:
        user_input: User's input message
        base_prompt: Base system prompt
        
    Returns:
        Enhanced prompt with Mermaid instructions
    """
    if should_generate_mermaid(user_input):
        # Scenario 1: Must generate diagram
        mermaid_instruction = """
IMPORTANT: The user has requested a diagram (flowchart, activity diagram, state machine diagram, or model diagram). 
You MUST include a Mermaid diagram in your response. Format it as:

```mermaid
[your mermaid diagram code here]
```

Common Mermaid diagram types:
- Flowchart: Use "flowchart TD" or "flowchart LR"
- Activity Diagram: Use "flowchart TD" with activity nodes
- State Machine: Use "stateDiagram-v2"
- Sequence Diagram: Use "sequenceDiagram"
- Class Diagram: Use "classDiagram"

Make sure the diagram accurately represents the requested model or process.
"""
    else:
        # Scenario 2: Optional for SysML (model decides)
        user_lower = user_input.lower()
        if any(keyword in user_lower for keyword in ['sysml', 'system model', 'system diagram']):
            mermaid_instruction = """
Note: If a SysML diagram would help the user understand the system model better, you may include a Mermaid diagram.
Format it as:

```mermaid
[your mermaid diagram code here]
```

This is optional - only include if it adds value to the explanation.
"""
        else:
            mermaid_instruction = ""
    
    if mermaid_instruction:
        return base_prompt + "\n\n" + mermaid_instruction
    
    return base_prompt

