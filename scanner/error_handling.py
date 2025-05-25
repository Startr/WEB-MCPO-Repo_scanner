"""
Robust Error Handling System for Repo Scanner

This module provides:
- Custom exception classes for different error types
- Error context manager for consistent handling
- Recovery strategies and retry mechanisms
- Comprehensive logging and monitoring
"""

import functools
import logging
import time
import traceback
from contextlib import contextmanager
from enum import Enum
from typing import Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, asdict
import json

# Import Flask current_app, but handle the case when Flask is not installed
try:
    from flask import current_app
except ImportError:
    current_app = None

class ErrorSeverity(Enum):
    """Error severity levels for categorization and handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better handling and recovery"""
    VALIDATION = "validation"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    GIT_OPERATION = "git_operation"
    PROCESSING = "processing"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    repo_url: Optional[str] = None
    file_path: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScannerError(Exception):
    """Base exception class for all scanner-related errors"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None,
        recoverable: bool = True,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext("unknown", "unknown")
        self.original_exception = original_exception
        self.recoverable = recoverable
        self.user_message = user_message or self._generate_user_message()
        self.timestamp = time.time()
        self.error_id = self._generate_error_id()

    def _generate_error_id(self) -> str:
        """Generate a unique error ID for tracking"""
        import uuid
        return f"ERR-{int(self.timestamp)}-{str(uuid.uuid4())[:8]}"

    def _generate_user_message(self) -> str:
        """Generate a user-friendly error message"""
        category_messages = {
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your data and try again.",
            ErrorCategory.NETWORK: "Network connectivity issue. Please check your connection and retry.",
            ErrorCategory.FILESYSTEM: "File system operation failed. Please check permissions and disk space.",
            ErrorCategory.GIT_OPERATION: "Git operation failed. Please check repository URL and access permissions.",
            ErrorCategory.PROCESSING: "Processing error occurred. Please try again later.",
            ErrorCategory.SYSTEM: "System error occurred. Please contact support if the issue persists.",
            ErrorCategory.EXTERNAL_SERVICE: "External service unavailable. Please try again later."
        }
        return category_messages.get(self.category, "An unexpected error occurred. Please try again.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "context": self.context.to_dict() if self.context else None,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class ValidationError(ScannerError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        self.field = field
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            **kwargs
        )


class NetworkError(ScannerError):
    """Raised when network operations fail"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class GitOperationError(ScannerError):
    """Raised when git operations fail"""
    
    def __init__(self, message: str, git_command: str = None, **kwargs):
        self.git_command = git_command
        super().__init__(
            message,
            category=ErrorCategory.GIT_OPERATION,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class FileSystemError(ScannerError):
    """Raised when filesystem operations fail"""
    
    def __init__(self, message: str, path: str = None, **kwargs):
        self.path = path
        super().__init__(
            message,
            category=ErrorCategory.FILESYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class ProcessingError(ScannerError):
    """Raised when file processing fails"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class SystemError(ScannerError):
    """Raised when system-level errors occur"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ErrorHandler:
    """Centralized error handler with logging and recovery strategies"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts = {}
        self.recovery_strategies = {}

    def register_recovery_strategy(
        self, 
        error_category: ErrorCategory, 
        strategy: Callable
    ):
        """Register a recovery strategy for a specific error category"""
        self.recovery_strategies[error_category] = strategy

    def handle_error(
        self, 
        error: Union[ScannerError, Exception], 
        context: Optional[ErrorContext] = None
    ) -> ScannerError:
        """Handle an error with appropriate logging and recovery attempts"""
        
        # Convert regular exceptions to ScannerError
        if not isinstance(error, ScannerError):
            scanner_error = ScannerError(
                message=str(error),
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_exception=error
            )
        else:
            scanner_error = error
            # Important fix: Always use the provided context if available
            if context:
                scanner_error.context = context

        # Log the error
        self._log_error(scanner_error)
        
        # Track error frequency
        self._track_error(scanner_error)
        
        # Attempt recovery if applicable
        if scanner_error.recoverable:
            self._attempt_recovery(scanner_error)
        
        return scanner_error

    def _log_error(self, error: ScannerError):
        """Log error with appropriate level and context"""
        log_data = error.to_dict()
        log_message = f"[{error.error_id}] {error.message}"
        
        if error.context:
            log_message += f" | Operation: {error.context.operation} | Component: {error.context.component}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"error_data": log_data})
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra={"error_data": log_data})
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={"error_data": log_data})
        else:
            self.logger.info(log_message, extra={"error_data": log_data})

    def _track_error(self, error: ScannerError):
        """Track error frequency for monitoring"""
        # Fix: Use the actual context operation instead of 'unknown'
        key = f"{error.category.value}:{error.context.operation}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    def _attempt_recovery(self, error: ScannerError):
        """Attempt to recover from error using registered strategies"""
        strategy = self.recovery_strategies.get(error.category)
        if strategy:
            try:
                strategy(error)
            except Exception as recovery_error:
                self.logger.error(
                    f"Recovery strategy failed for {error.error_id}: {recovery_error}"
                )

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics for monitoring"""
        return self.error_counts.copy()


class RetryConfig:
    """Configuration for retry mechanisms"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        exponential_backoff: bool = True,
        max_delay: float = 60.0,
        retryable_categories: Optional[set] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.exponential_backoff = exponential_backoff
        self.max_delay = max_delay
        self.retryable_categories = retryable_categories or {
            ErrorCategory.NETWORK,
            ErrorCategory.GIT_OPERATION,
            ErrorCategory.EXTERNAL_SERVICE
        }


def with_error_handling(
    operation: str,
    component: str,
    retry_config: Optional[RetryConfig] = None,
    context_data: Optional[Dict[str, Any]] = None
):
    """Decorator for adding comprehensive error handling to functions"""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get error handler from Flask app context or create default
            try:
                from flask import current_app
                error_handler = getattr(current_app, 'error_handler', None)
                if not error_handler:
                    error_handler = ErrorHandler(current_app.logger)
                    current_app.error_handler = error_handler
            except RuntimeError:
                # Outside Flask context, create basic handler
                import logging
                error_handler = ErrorHandler(logging.getLogger(__name__))

            context = ErrorContext(
                operation=operation,
                component=component,
                additional_data=context_data
            )
            
            retry_cfg = retry_config or RetryConfig()
            attempt = 0
            last_error = None
            
            while attempt < retry_cfg.max_attempts:
                try:
                    return func(*args, **kwargs)
                    
                except ScannerError as e:
                    last_error = e
                    handled_error = error_handler.handle_error(e, context)
                    
                    if (not handled_error.recoverable or 
                        handled_error.category not in retry_cfg.retryable_categories or
                        attempt >= retry_cfg.max_attempts - 1):
                        raise handled_error
                        
                except Exception as e:
                    last_error = e
                    handled_error = error_handler.handle_error(e, context)
                    
                    if attempt >= retry_cfg.max_attempts - 1:
                        raise handled_error
                
                # Calculate delay for next attempt
                if retry_cfg.exponential_backoff:
                    delay = min(
                        retry_cfg.base_delay * (2 ** attempt),
                        retry_cfg.max_delay
                    )
                else:
                    delay = retry_cfg.base_delay
                
                attempt += 1
                if attempt < retry_cfg.max_attempts:
                    time.sleep(delay)
            
            # If we get here, all retries failed
            if isinstance(last_error, ScannerError):
                raise last_error
            else:
                raise error_handler.handle_error(last_error, context)
                
        return wrapper
    return decorator


@contextmanager
def error_context(
    operation: str,
    component: str,
    **context_kwargs
):
    """Context manager for handling errors within a specific operation"""
    context = ErrorContext(
        operation=operation,
        component=component,
        additional_data=context_kwargs
    )
    
    try:
        from flask import current_app
        error_handler = getattr(current_app, 'error_handler', None)
        if not error_handler:
            error_handler = ErrorHandler(current_app.logger)
            current_app.error_handler = error_handler
    except RuntimeError:
        import logging
        error_handler = ErrorHandler(logging.getLogger(__name__))
    
    try:
        yield context
    except Exception as e:
        handled_error = error_handler.handle_error(e, context)
        raise handled_error


def safe_operation(
    default_return=None,
    log_errors=True,
    reraise_critical=True
):
    """Decorator for operations that should not crash the application"""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ScannerError as e:
                if log_errors:
                    logging.getLogger(__name__).error(
                        f"Safe operation failed: {func.__name__}: {e.message}"
                    )
                
                if reraise_critical and e.severity == ErrorSeverity.CRITICAL:
                    raise
                    
                return default_return
                
            except Exception as e:
                if log_errors:
                    logging.getLogger(__name__).error(
                        f"Safe operation failed: {func.__name__}: {str(e)}"
                    )
                return default_return
                
        return wrapper
    return decorator


@with_error_handling("complex_op", "test_component")
def complex_operation(scenario):
    """Test function for complex error scenarios"""
    if scenario == "validation":
        raise ValidationError("Invalid input", field="email")
    elif scenario == "network":
        raise NetworkError("Connection failed")
    elif scenario == "system":
        raise SystemError("System failure")
    return "success"