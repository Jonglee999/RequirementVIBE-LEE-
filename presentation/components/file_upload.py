"""
File Upload Component for ReqVibe

This module provides a secure file upload component for Streamlit that:
- Supports PDF, Word (.docx), and ReqIF (.reqif) formats
- Allows multiple file uploads
- Enforces 10MB total size limit
- Shows clear error messages
- Processes files using Unstructured API
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import tempfile
import os

# Domain Services
from domain.documents.unstructured import (
    process_multiple_documents,
    validate_file,
    UnstructuredServiceError,
    get_unstructured_api_key,
    MAX_FILE_SIZE
)


def render_file_upload():
    """
    Render the file upload component in the sidebar.
    
    This component allows users to upload documents for processing
    and automatically processes them using the Unstructured API.
    """
    st.markdown(
        "<div style='margin-top: 1.5rem; margin-bottom: 1rem;'>"
        "<h3 style='color: #8e8ea0; font-size: 0.9rem; font-weight: 600; "
        "text-transform: uppercase; letter-spacing: 0.5px;'>Document Upload</h3>"
        "</div>",
        unsafe_allow_html=True
    )
    
    # Check authentication
    if not st.session_state.authenticated:
        st.info("Please log in to upload documents")
        return
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=["pdf", "docx", "reqif"],
        accept_multiple_files=True,
        help="Upload PDF, Word (.docx), or ReqIF (.reqif) files. Maximum 10MB total.",
        key="file_uploader"
    )
    
    # Display file information
    if uploaded_files:
        # Calculate total size
        total_size = sum(file.size for file in uploaded_files)
        total_size_mb = total_size / (1024 * 1024)
        
        # Validate total size
        if total_size > MAX_FILE_SIZE:
            st.error(
                f"Total file size ({total_size_mb:.2f}MB) exceeds the maximum limit of 10MB. "
                "Please upload smaller files or reduce the number of files."
            )
            return
        
        # Display uploaded files info
        st.markdown("**Uploaded Files:**")
        file_info_html = "<div style='margin-bottom: 0.75rem;'>"
        for i, file in enumerate(uploaded_files, 1):
            file_size_kb = file.size / 1024
            file_ext = os.path.splitext(file.name)[1].upper()
            file_info_html += (
                f"<div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>"
                f"{i}. {file.name} ({file_size_kb:.2f} KB, {file_ext})"
                f"</div>"
            )
        file_info_html += f"<div style='color: #8e8ea0; font-size: 0.75rem; margin-top: 0.25rem;'>"
        file_info_html += f"Total: {total_size_mb:.2f} MB / 10 MB</div>"
        file_info_html += "</div>"
        st.markdown(file_info_html, unsafe_allow_html=True)
        
        # Validate individual files
        invalid_files = []
        for file in uploaded_files:
            file_bytes = file.getvalue()
            is_valid, error_msg = validate_file(file_bytes, file.name)
            if not is_valid:
                invalid_files.append((file.name, error_msg))
        
        if invalid_files:
            st.error("**Invalid Files:**")
            for filename, error_msg in invalid_files:
                st.error(f"- {filename}: {error_msg}")
            return
        
        # Process button
        if st.button("Process Documents", use_container_width=True, key="process_documents_button"):
            process_uploaded_files(uploaded_files)
    
    # Display processing results if available
    if st.session_state.get("document_processing_results"):
        display_processing_results()


def process_uploaded_files(uploaded_files: List):
    """
    Process uploaded files using Unstructured API.
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
    """
    # Check if API key is set
    try:
        get_unstructured_api_key()
    except UnstructuredServiceError as e:
        st.error(str(e))
        st.info(
            "To use document processing, please set the UNSTRUCTURED_API_KEY "
            "environment variable with your API key."
        )
        return
    
    # Prepare files for processing
    files_to_process = []
    for file in uploaded_files:
        file_bytes = file.getvalue()
        files_to_process.append((file_bytes, file.name))
    
    # Process files
    try:
        with st.spinner("Processing documents... This may take a few moments."):
            results = process_multiple_documents(files_to_process, strategy="fast")
            
            # Store results in session state
            st.session_state.document_processing_results = results
            st.session_state.document_processing_error = None
            
            # Also store formatted output for easy access
            from domain.documents.unstructured import format_structured_output
            st.session_state.document_processing_formatted = format_structured_output(results)
            
            # Build GraphRAG index
            with st.spinner("Building knowledge graph index..."):
                from infrastructure.graphrag.service import build_graphrag_index
                graphrag_index = build_graphrag_index(results)
                
                # Store GraphRAG index in session state (serialized)
                st.session_state.graphrag_index = graphrag_index.to_dict()
                st.session_state.graphrag_index_built = True
            
            st.success(f"✅ Documents processed successfully! You can now ask questions about the documents.")
            st.rerun()
            
    except UnstructuredServiceError as e:
        st.session_state.document_processing_error = str(e)
        st.session_state.document_processing_results = None
        st.error(f"Error processing documents: {str(e)}")
    except Exception as e:
        st.session_state.document_processing_error = str(e)
        st.session_state.document_processing_results = None
        st.error(f"Unexpected error: {str(e)}")


def display_processing_results():
    """Display the results of document processing."""
    results = st.session_state.document_processing_results
    
    st.markdown("<div style='margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("**Processing Results:**")
    
    # Summary
    summary_html = (
        f"<div style='padding: 0.75rem; background-color: #343541; "
        f"border-radius: 6px; border: 1px solid #565869; margin-bottom: 1rem;'>"
        f"<div style='color: #8e8ea0; font-size: 0.75rem; margin-bottom: 0.25rem;'>"
        f"Summary</div>"
        f"<div style='color: #ececf1; font-size: 0.9rem;'>"
        f"Files: {results['total_files']} | "
        f"Elements: {results['total_elements']} | "
        f"Size: {results['total_size'] / 1024:.2f} KB"
        f"</div>"
        f"</div>"
    )
    st.markdown(summary_html, unsafe_allow_html=True)
    
    # Show formatted output in expander
    if st.session_state.get("document_processing_formatted"):
        with st.expander("View Structured Output", expanded=False):
            st.text(st.session_state.document_processing_formatted)
    
    # Option to download results as JSON
    import json
    results_json = json.dumps(results, indent=2, default=str)
    st.download_button(
        label="Download Results (JSON)",
        data=results_json,
        file_name="document_processing_results.json",
        mime="application/json",
        use_container_width=True,
        key="download_results_button"
    )
    
    # Note: GraphRAG is now automatically available for document-related questions
    # Users can ask questions directly without needing to send results to chat
    
    st.markdown("</div>", unsafe_allow_html=True)

