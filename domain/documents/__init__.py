"""Document processing domain services."""
from .srs import generate_ieee830_srs_from_conversation
from .unstructured import (
    process_multiple_documents,
    process_document,
    validate_file,
    format_structured_output,
    get_unstructured_api_key,
    UnstructuredServiceError,
    MAX_FILE_SIZE
)

__all__ = [
    'generate_ieee830_srs_from_conversation',
    'process_multiple_documents',
    'process_document',
    'validate_file',
    'format_structured_output',
    'get_unstructured_api_key',
    'UnstructuredServiceError',
    'MAX_FILE_SIZE'
]
