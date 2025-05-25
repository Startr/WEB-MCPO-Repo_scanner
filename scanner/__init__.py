"""
Scanner Package for Repo Scanner Application

This package contains the core functionality for scanning repositories and identifying TODOs.
It provides error handling, pattern recognition, and related utility functions.
"""

from .error_handling import (
    # Error classes
    ScannerError, ValidationError, NetworkError, GitOperationError,
    FileSystemError, ProcessingError, SystemError,
    
    # Error handling utilities
    ErrorHandler, RetryConfig, ErrorContext, ErrorCategory, ErrorSeverity,
    
    # Decorators and context managers
    with_error_handling, error_context, safe_operation
)

# Version of the scanner package
__version__ = '1.0.0'