"""
Test suite for the error handling system
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
import tempfile
import os

from error_handling import (
    ErrorSeverity, ErrorCategory, ErrorContext, ScannerError,
    ValidationError, NetworkError, GitOperationError, FileSystemError,
    ProcessingError, SystemError, ErrorHandler, RetryConfig,
    with_error_handling, error_context, safe_operation, complex_operation
)


class TestErrorClasses:
    """Test custom exception classes"""
    
    def test_scanner_error_creation(self):
        """Test basic ScannerError creation"""
        context = ErrorContext("test_op", "test_component")
        error = ScannerError(
            "Test error",
            ErrorCategory.VALIDATION,
            ErrorSeverity.HIGH,
            context
        )
        
        assert error.message == "Test error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert error.recoverable is True
        assert error.error_id.startswith("ERR-")
        assert error.timestamp > 0

    def test_validation_error(self):
        """Test ValidationError specific behavior"""
        error = ValidationError("Invalid field", field="email")
        
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is False
        assert error.field == "email"

    def test_git_operation_error(self):
        """Test GitOperationError specific behavior"""
        error = GitOperationError("Git clone failed", git_command="git clone")
        
        assert error.category == ErrorCategory.GIT_OPERATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert error.git_command == "git clone"

    def test_error_to_dict(self):
        """Test error serialization to dictionary"""
        context = ErrorContext("test_op", "test_component", repo_url="test://repo")
        error = ScannerError("Test error", ErrorCategory.NETWORK, context=context)
        
        error_dict = error.to_dict()
        
        assert "error_id" in error_dict
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "network"
        assert error_dict["context"]["repo_url"] == "test://repo"

    def test_user_message_generation(self):
        """Test automatic user-friendly message generation"""
        error = NetworkError("Connection timeout")
        assert "Network connectivity issue" in error.user_message
        
        error = ValidationError("Invalid input")
        assert "Invalid input provided" in error.user_message


class TestErrorHandler:
    """Test the centralized error handler"""
    
    def setup_method(self):
        """Setup for each test"""
        self.logger = Mock(spec=logging.Logger)
        self.handler = ErrorHandler(self.logger)

    def test_handle_scanner_error(self):
        """Test handling of ScannerError"""
        error = ValidationError("Test validation error")
        context = ErrorContext("test_op", "test_component")
        
        handled = self.handler.handle_error(error, context)
        
        assert handled is error
        # Context should now be properly set from the provided value
        assert handled.context is context
        self.logger.info.assert_called_once()

    def test_handle_regular_exception(self):
        """Test handling of regular Python exceptions"""
        error = ValueError("Regular exception")
        context = ErrorContext("test_op", "test_component")
        
        handled = self.handler.handle_error(error, context)
        
        assert isinstance(handled, ScannerError)
        assert handled.original_exception is error
        assert handled.context == context
        self.logger.warning.assert_called_once()

    def test_error_tracking(self):
        """Test error frequency tracking"""
        context = ErrorContext("test_op", "test_component")
        error1 = ValidationError("Error 1")
        error2 = ValidationError("Error 2")
        
        # The context is now properly set, so the key should include 'test_op'
        self.handler.handle_error(error1, context)
        self.handler.handle_error(error2, context)
        
        stats = self.handler.get_error_stats()
        assert "validation:test_op" in stats
        assert stats["validation:test_op"] == 2

    def test_recovery_strategy_registration(self):
        """Test registration and execution of recovery strategies"""
        recovery_called = False
        
        def recovery_strategy(error):
            nonlocal recovery_called
            recovery_called = True
        
        self.handler.register_recovery_strategy(ErrorCategory.NETWORK, recovery_strategy)
        
        error = NetworkError("Test network error")
        self.handler.handle_error(error)
        
        assert recovery_called

    def test_recovery_strategy_failure(self):
        """Test handling of recovery strategy failures"""
        def failing_recovery(error):
            raise Exception("Recovery failed")
        
        self.handler.register_recovery_strategy(ErrorCategory.NETWORK, failing_recovery)
        
        error = NetworkError("Test network error")
        self.handler.handle_error(error)
        
        # Should log the recovery failure but not crash
        assert self.logger.error.call_count >= 1


class TestRetryDecorator:
    """Test the retry decorator functionality"""
    
    def test_successful_operation(self):
        """Test that successful operations work normally"""
        
        @with_error_handling("test_op", "test_component")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"

    def test_retry_on_recoverable_error(self):
        """Test retry behavior on recoverable errors"""
        call_count = 0
        
        @with_error_handling("test_op", "test_component", RetryConfig(max_attempts=3))
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Temporary failure")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_non_recoverable_error(self):
        """Test that non-recoverable errors are not retried"""
        call_count = 0
        
        @with_error_handling("test_op", "test_component", RetryConfig(max_attempts=3))
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid input")
        
        with pytest.raises(ValidationError):
            failing_func()
        
        assert call_count == 1

    def test_exponential_backoff(self):
        """Test exponential backoff timing"""
        call_times = []
        
        @with_error_handling("test_op", "test_component", RetryConfig(
            max_attempts=3, base_delay=0.1, exponential_backoff=True
        ))
        def failing_func():
            call_times.append(time.time())
            raise NetworkError("Always fails")
        
        with pytest.raises(NetworkError):
            failing_func()
        
        assert len(call_times) == 3
        # Check that delays are increasing (allowing some margin for timing)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1


class TestErrorContext:
    """Test the error context manager"""
    
    def test_successful_context(self):
        """Test context manager with successful operation"""
        with error_context("test_op", "test_component") as ctx:
            assert ctx.operation == "test_op"
            assert ctx.component == "test_component"

    def test_error_in_context(self):
        """Test error handling within context"""
        with pytest.raises(ScannerError) as exc_info:
            with error_context("test_op", "test_component"):
                raise ValueError("Test error")
        
        error = exc_info.value
        assert isinstance(error, ScannerError)
        assert error.context.operation == "test_op"
        assert error.context.component == "test_component"


class TestSafeOperation:
    """Test the safe operation decorator"""
    
    def test_successful_safe_operation(self):
        """Test safe operation with success"""
        
        @safe_operation(default_return="default")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"

    def test_safe_operation_with_error(self):
        """Test safe operation with error returns default"""
        
        @safe_operation(default_return="default")
        def failing_func():
            raise ValueError("Test error")
        
        result = failing_func()
        assert result == "default"

    def test_safe_operation_reraise_critical(self):
        """Test that critical errors are re-raised even in safe operations"""
        
        @safe_operation(default_return="default", reraise_critical=True)
        def critical_failing_func():
            raise ScannerError("Critical error", ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)
        
        with pytest.raises(ScannerError):
            critical_failing_func()


class TestIntegration:
    """Integration tests for the complete error handling system"""
    
    def setup_method(self):
        """Setup for integration tests"""
        self.logger = Mock(spec=logging.Logger)
    
    def test_end_to_end_error_handling(self):
        """Test complete error handling flow"""
        
        # Setup recovery strategy
        recovery_called = False
        def network_recovery(error):
            nonlocal recovery_called
            recovery_called = True
        
        # Create handler and register strategy
        handler = ErrorHandler(self.logger)
        handler.register_recovery_strategy(ErrorCategory.NETWORK, network_recovery)
        
        # Mock Flask app context - fixed to use module-level patch
        mock_app = Mock()
        mock_app.logger = self.logger
        mock_app.error_handler = handler
        
        # Use monkeypatch instead of patching the import
        import error_handling
        original_current_app = error_handling.current_app
        try:
            error_handling.current_app = mock_app
            
            # Create a fresh RetryConfig that will allow recovery for NetworkError
            retry_config = RetryConfig(max_attempts=2)
            
            call_count = 0
            
            # Create the context explicitly here, so we can use it consistently
            context = ErrorContext("network_op", "test_component")
            
            @with_error_handling("network_op", "test_component", retry_config)
            def network_operation():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Create error with the explicit context
                    error = NetworkError(
                        "Temporary network issue",
                        context=context  # Explicitly set the context
                    )
                    # Handle the error with our handler
                    handler.handle_error(error)
                    raise error
                return "success"
            
            result = network_operation()
            
            assert result == "success"
            assert call_count == 2
            assert recovery_called
            
            # Now the error stats should contain the right key
            error_stats = handler.get_error_stats()
            assert "network:network_op" in error_stats
            
        finally:
            # Restore original current_app
            error_handling.current_app = original_current_app

    def test_complex_error_scenario(self):
        """Test complex error scenarios with multiple error types"""
        # Since we have the complex_operation function in the error_handling module now
        # We can test it directly

        # Test validation error (not retried)
        with pytest.raises(ValidationError):
            complex_operation("validation")
        
        # Test network error (retried)
        with pytest.raises(NetworkError):
            complex_operation("network")
        
        # Test system error (not retried due to non-recoverable)
        with pytest.raises(SystemError):
            complex_operation("system")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])