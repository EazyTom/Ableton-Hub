"""Base worker class for background processing."""

from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from ...utils.logging import get_logger


class BaseWorker(QObject):
    """Base class for background workers.
    
    This class provides common functionality for all worker classes,
    standardizing patterns and reducing code duplication.
    """
    
    finished = pyqtSignal(object)  # Generic result
    error = pyqtSignal(str)  # Error message
    progress = pyqtSignal(int, int, str)  # current, total, message
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the base worker.
        
        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._cancelled = False
    
    def run(self) -> None:
        """Execute the worker task.
        
        This method should be overridden in subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def cancel(self) -> None:
        """Cancel the worker operation."""
        self._cancelled = True
        self.logger.debug(f"{self.__class__.__name__} cancellation requested")
    
    def is_cancelled(self) -> bool:
        """Check if the worker has been cancelled.
        
        Returns:
            True if cancelled, False otherwise.
        """
        return self._cancelled
    
    def emit_error(self, error_msg: str, context: Optional[dict] = None) -> None:
        """Emit an error signal with context information.
        
        Args:
            error_msg: Error message to emit.
            context: Optional dictionary with additional context (e.g., project_id, file_path).
        """
        # Build detailed error message with context
        error_details = [f"{self.__class__.__name__} error: {error_msg}"]
        
        # Add worker state
        error_details.append(f"  Cancelled: {self._cancelled}")
        
        # Add context if provided
        if context:
            for key, value in context.items():
                error_details.append(f"  {key}: {value}")
        
        full_error_msg = "\n".join(error_details)
        self.logger.error(full_error_msg)
        self.error.emit(error_msg)
    
    def emit_progress(self, current: int, total: int, message: str = "") -> None:
        """Emit a progress signal.
        
        Args:
            current: Current progress value.
            total: Total items to process.
            message: Optional progress message.
        """
        self.progress.emit(current, total, message)
