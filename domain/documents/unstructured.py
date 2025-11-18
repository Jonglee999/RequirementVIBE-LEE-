"""
Unstructured API Service for Document Processing

This service handles document processing using Unstructured Serverless API.
It supports multiple file formats (PDF, Word, ReqIF) and processes them
using the partition pipeline to extract structured content.

Uses the official unstructured-client Python SDK for better SSL handling.
"""

import os
import io
from typing import List, Dict, Any, Optional
import json
import time
import warnings

# Always import requests (needed for fallback and type hints)
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
try:
    from urllib3.exceptions import InsecureRequestWarning
except ImportError:
    # Fallback for older urllib3 versions or when urllib3 is bundled with requests
    try:
        import urllib3
        InsecureRequestWarning = getattr(urllib3.exceptions, 'InsecureRequestWarning', None)
    except (ImportError, AttributeError):
        InsecureRequestWarning = None

# Try to import the official SDK, fall back to requests if not available
try:
    from unstructured_client import UnstructuredClient
    from unstructured_client.models import shared, errors
    USE_OFFICIAL_SDK = True
except ImportError:
    USE_OFFICIAL_SDK = False

# Try to import httpx for error handling (used by SDK)
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# API URL - should use the URL provided when account was created
# Default is https://api.unstructuredapp.io/general/v0/general according to docs
# But we allow override via environment variable
UNSTRUCTURED_API_URL = os.getenv(
    "UNSTRUCTURED_API_URL",
    "https://api.unstructured.io/general/v0/general"  # Fallback to common URL
)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


class UnstructuredServiceError(Exception):
    """Custom exception for Unstructured API service errors."""
    pass


def get_unstructured_api_key() -> Optional[str]:
    """
    Get the Unstructured API key from environment variable.
    
    Returns:
        Optional[str]: The API key if set, None otherwise
        
    Raises:
        UnstructuredServiceError: If API key is not set
    """
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not api_key:
        raise UnstructuredServiceError(
            "UNSTRUCTURED_API_KEY environment variable is not set. "
            "Please set it to use document processing functionality."
        )
    return api_key


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file format and size.
    
    Args:
        file_bytes: The file content as bytes
        filename: The name of the file
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        return False, f"File '{filename}' is too large ({size_mb:.2f}MB). Maximum size is 10MB."
    
    # Check file extension
    allowed_extensions = {'.pdf', '.docx', '.reqif'}
    file_ext = os.path.splitext(filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        return False, (
            f"File '{filename}' has unsupported format '{file_ext}'. "
            f"Supported formats: PDF (.pdf), Word (.docx), ReqIF (.reqif)"
        )
    
    return True, None


def _create_unstructured_client(api_key: str, disable_ssl_verify: bool = False):
    """
    Create an UnstructuredClient instance - simplified to match working test file.
    
    Args:
        api_key: The API key for authentication
        disable_ssl_verify: Whether to disable SSL verification (for testing only, not used with SDK)
        
    Returns:
        UnstructuredClient: Configured client instance
    """
    if USE_OFFICIAL_SDK:
        try:
            # Simple initialization matching the working test file
            client = UnstructuredClient(
                api_key_auth=api_key
            )
            return client
        except Exception as e:
            raise UnstructuredServiceError(
                f"Failed to initialize UnstructuredClient: {str(e)}. "
                "Please check the SDK documentation for the correct initialization method."
            )
    else:
        return None


def _create_requests_session() -> requests.Session:
    """
    Create a requests session with retry logic and SSL configuration.
    Fallback method when official SDK is not available.
    
    Returns:
        requests.Session: Configured session with retry logic
    """
    # Always create a session (needed for fallback even if SDK is available)
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
        allowed_methods=["POST", "GET"],  # Methods to retry
        raise_on_status=False  # Don't raise on status, handle it manually
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


def process_document(
    file_bytes: bytes,
    filename: str,
    strategy: str = "fast",
    disable_ssl_verify: bool = False
) -> List[Dict[str, Any]]:
    """
    Process a single document using Unstructured Serverless API.
    
    Args:
        file_bytes: The file content as bytes
        filename: The name of the file
        strategy: Processing strategy (default: "fast")
                  Options: "fast", "hi_res", "ocr_only", "auto"
        disable_ssl_verify: Whether to disable SSL verification (for testing only)
        
    Returns:
        List[Dict[str, Any]]: Structured output from the partition pipeline
        
    Raises:
        UnstructuredServiceError: If processing fails
    """
    # Validate file
    is_valid, error_message = validate_file(file_bytes, filename)
    if not is_valid:
        raise UnstructuredServiceError(error_message)
    
    # Get API key
    api_key = get_unstructured_api_key()
    
    # Use local variable for SSL verification setting (may be updated if SSL errors detected)
    should_disable_ssl = disable_ssl_verify
    
    # Use official SDK if available (recommended)
    use_sdk = USE_OFFICIAL_SDK
    
    if use_sdk:
        try:
            client = _create_unstructured_client(api_key, disable_ssl_verify=should_disable_ssl)
            
            # Call partition API using SDK - matching working test file pattern
            try:
                # Map strategy string to Strategy enum
                strategy_map = {
                    "fast": shared.Strategy.FAST,
                    "hi_res": shared.Strategy.HI_RES,
                    "ocr_only": shared.Strategy.OCR_ONLY,
                    "auto": shared.Strategy.AUTO,
                }
                strategy_enum = strategy_map.get(strategy.lower(), shared.Strategy.AUTO)
                
                # Use dictionary-based request structure matching the working test file
                # The SDK accepts raw bytes directly (not BytesIO)
                # Based on validation errors, it expects bytes, IO, or BufferedReader
                req = {
                    "partition_parameters": {
                        "files": {
                            "content": file_bytes,  # Pass raw bytes directly
                            "file_name": filename,
                        },
                        "strategy": strategy_enum,
                    }
                }
                
                # Call partition method with dictionary request (synchronous)
                result = client.general.partition(request=req)
                
                # Extract elements from response - direct access like test file
                if hasattr(result, 'elements') and result.elements:
                    elements = result.elements
                    # Convert elements to list of dicts
                    element_dicts = []
                    for element in elements:
                        if isinstance(element, dict):
                            element_dicts.append(element)
                        elif hasattr(element, '__dict__'):
                            # Convert object to dict
                            element_dict = vars(element)
                            element_dicts.append(element_dict)
                        else:
                            # Convert to string representation
                            element_dicts.append({"text": str(element)})
                    return element_dicts
                else:
                    return []
                
            except errors.UnstructuredClientError as e:
                # Handle SDK-specific errors
                raise UnstructuredServiceError(
                    f"Unstructured API error: {str(e)}"
                )
            except (AttributeError, TypeError) as e:
                # If partition method structure is different, try alternative
                raise UnstructuredServiceError(
                    f"SDK API structure may have changed: {str(e)}. "
                    f"Please check unstructured-client documentation for the correct usage."
                )
                
        except UnstructuredServiceError:
            raise
        except Exception as e:
            # Check if this is an SSL/connection error from httpx (used by SDK)
            ssl_error_detected = False
            error_str = str(e).lower()
            
            # Check for SSL-related errors
            if HAS_HTTPX:
                # Check if it's an httpx.ConnectError
                if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout)):
                    ssl_error_detected = True
                # Also check for SSL-related error messages
                elif any(ssl_term in error_str for ssl_term in [
                    'ssl', 'tls', 'certificate', 'unexpected_eof', 
                    'eof occurred', 'protocol violation'
                ]):
                    ssl_error_detected = True
            elif any(ssl_term in error_str for ssl_term in [
                'ssl', 'tls', 'certificate', 'unexpected_eof', 
                'eof occurred', 'protocol violation'
            ]):
                ssl_error_detected = True
            
            # If SDK fails, fall back to requests method
            # Log the error but don't raise yet - try requests method
            if ssl_error_detected:
                print(f"Warning: SSL/connection error with SDK: {str(e)}. Falling back to requests method with SSL verification disabled...")
                # Automatically disable SSL verification for fallback
                should_disable_ssl = True
            else:
                print(f"Warning: SDK failed: {str(e)}. Falling back to requests method...")
            use_sdk = False  # Force fallback
    
    # Fallback to requests method if SDK is not available or failed
    if not use_sdk:
        # Create session for requests - disable SSL verification if needed
        session = _create_requests_session(disable_ssl_verify=should_disable_ssl)
        if session is None:
            raise UnstructuredServiceError(
                f"Failed to create requests session. "
                "Please ensure requests and urllib3 are properly installed."
            )
        
        # Prepare request according to official documentation
        # API key should be passed as 'unstructured-api-key' header, not Authorization Bearer
        # Reference: https://docs.unstructured.io/api-reference/partition/overview
        headers = {
            "unstructured-api-key": api_key,
            "accept": "application/json",
        }
        
        # Determine file type from extension
        file_ext = os.path.splitext(filename.lower())[1]
        content_type_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.reqif': 'application/reqif+xml',
        }
        content_type = content_type_map.get(file_ext, 'application/octet-stream')
        
        # Prepare files and data for multipart/form-data request
        files = {
            'files': (filename, file_bytes, content_type)
        }
        
        # Form data parameters according to official documentation
        # The curl example shows: content_type, strategy, output_format
        # Reference: https://docs.unstructured.io/api-reference/partition/overview
        data = {
            'strategy': strategy,
            'output_format': 'application/json',  # As shown in curl example
        }
        
        try:
            # Make API request - configure SSL verification based on parameter
            # When should_disable_ssl is True, explicitly set verify=False
            verify_ssl = not should_disable_ssl
            
            response = session.post(
                UNSTRUCTURED_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=300,
                verify=verify_ssl  # Explicitly set SSL verification
            )
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'detail' in error_data:
                        error_msg += f": {error_data['detail']}"
                    elif 'message' in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text[:200]}"
                raise UnstructuredServiceError(error_msg)
            
            # Parse response
            result = response.json()
            
            # The API returns a list of dictionaries with structured content
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and 'elements' in result:
                return result['elements']
            else:
                return [result] if isinstance(result, dict) else result
                
        except requests.exceptions.SSLError as e:
            # If SSL error and SSL verification was enabled, retry with it disabled
            # This is a common issue with some networks/proxies - disable SSL verification as fallback
            if not should_disable_ssl:
                if InsecureRequestWarning is not None:
                    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                print(f"Warning: SSL error encountered. Retrying with SSL verification disabled...")
                try:
                    return process_document(file_bytes, filename, strategy, disable_ssl_verify=True)
                except Exception as retry_error:
                    raise UnstructuredServiceError(
                        f"SSL error while processing '{filename}': {str(e)}. "
                        f"Retry with SSL verification disabled also failed: {str(retry_error)}. "
                        "This may indicate a network or firewall issue."
                    )
            else:
                raise UnstructuredServiceError(
                    f"SSL error while processing '{filename}': {str(e)}. "
                    "Please check your network connection and SSL certificates."
                )
        except requests.exceptions.Timeout:
            raise UnstructuredServiceError(
                f"Request timeout while processing '{filename}'. "
                "The file may be too large or the server is taking too long to respond."
            )
        except requests.exceptions.RequestException as e:
            raise UnstructuredServiceError(
                f"Network error while processing '{filename}': {str(e)}"
            )
        except json.JSONDecodeError as e:
            raise UnstructuredServiceError(
                f"Failed to parse API response for '{filename}': {str(e)}"
            )
        except Exception as e:
            raise UnstructuredServiceError(
                f"Unexpected error while processing '{filename}': {str(e)}"
            )


def process_multiple_documents(
    files: List[tuple[bytes, str]],
    strategy: str = "fast",
    disable_ssl_verify: bool = False
) -> Dict[str, Any]:
    """
    Process multiple documents and combine their outputs.
    
    Args:
        files: List of tuples (file_bytes, filename)
        strategy: Processing strategy (default: "fast")
        
    Returns:
        Dict[str, Any]: Combined structured output with metadata
        {
            'documents': [
                {
                    'filename': str,
                    'elements': List[Dict],
                    'element_count': int,
                    'file_size': int
                }
            ],
            'total_elements': int,
            'total_files': int,
            'total_size': int
        }
        
    Raises:
        UnstructuredServiceError: If processing fails
    """
    if not files:
        raise UnstructuredServiceError("No files provided for processing")
    
    # Validate total size
    total_size = sum(len(file_bytes) for file_bytes, _ in files)
    if total_size > MAX_FILE_SIZE:
        total_size_mb = total_size / (1024 * 1024)
        raise UnstructuredServiceError(
            f"Total combined file size ({total_size_mb:.2f}MB) exceeds the maximum limit of 10MB."
        )
    
    results = {
        'documents': [],
        'total_elements': 0,
        'total_files': len(files),
        'total_size': total_size
    }
    
    # Process each file
    for file_bytes, filename in files:
        try:
            elements = process_document(
                file_bytes, 
                filename, 
                strategy=strategy,
                disable_ssl_verify=disable_ssl_verify
            )
            
            document_result = {
                'filename': filename,
                'elements': elements,
                'element_count': len(elements),
                'file_size': len(file_bytes)
            }
            
            results['documents'].append(document_result)
            results['total_elements'] += len(elements)
            
        except UnstructuredServiceError as e:
            # Re-raise with filename context
            raise UnstructuredServiceError(f"Error processing '{filename}': {str(e)}")
    
    return results


def format_structured_output(result: Dict[str, Any]) -> str:
    """
    Format the structured output as a readable text string.
    
    Args:
        result: The combined structured output from process_multiple_documents
        
    Returns:
        str: Formatted text representation
    """
    output_lines = []
    output_lines.append(f"Processed {result['total_files']} file(s)")
    output_lines.append(f"Total elements: {result['total_elements']}")
    output_lines.append(f"Total size: {result['total_size'] / 1024:.2f} KB")
    output_lines.append("")
    
    for doc in result['documents']:
        output_lines.append(f"=== {doc['filename']} ===")
        output_lines.append(f"Elements: {doc['element_count']}, Size: {doc['file_size'] / 1024:.2f} KB")
        output_lines.append("")
        
        for i, element in enumerate(doc['elements'], 1):
            element_type = element.get('type', 'unknown')
            text = element.get('text', '')
            
            # Truncate long text for display
            if len(text) > 500:
                text = text[:500] + "..."
            
            output_lines.append(f"Element {i} ({element_type}):")
            output_lines.append(text)
            output_lines.append("")
    
    return "\n".join(output_lines)

