"""ViewController for managing view state and navigation."""

from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal

from ...utils.logging import get_logger
from ..managers.view_manager import ViewManager


class ViewController(QObject):
    """Manages view state and navigation.
    
    This controller provides a higher-level interface for view management,
    including state persistence and navigation history.
    """
    
    view_changed = pyqtSignal(str)  # View name
    view_state_changed = pyqtSignal(str, dict)  # view_name, state
    
    def __init__(self, view_manager: ViewManager, parent: Optional[QObject] = None):
        """Initialize the view controller.
        
        Args:
            view_manager: ViewManager instance to use for view switching.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._view_manager = view_manager
        self._view_states: Dict[str, dict] = {}  # view_name -> state dict
        
        # Connect to view manager signals
        self._view_manager.view_changed.connect(self._on_view_changed)
    
    def navigate_to(self, view_name: str, state: Optional[Dict] = None) -> bool:
        """Navigate to a view with optional state.
        
        Args:
            view_name: Name of the view to navigate to.
            state: Optional state dictionary to save with the view.
            
        Returns:
            True if navigation was successful, False otherwise.
        """
        success = self._view_manager.switch_to_view(view_name)
        if success and state:
            self._view_states[view_name] = state
            self.view_state_changed.emit(view_name, state)
        return success
    
    def get_view_state(self, view_name: str) -> Dict:
        """Get saved state for a view.
        
        Args:
            view_name: Name of the view.
            
        Returns:
            State dictionary, empty dict if no state saved.
        """
        return self._view_states.get(view_name, {})
    
    def set_view_state(self, view_name: str, state: Dict) -> None:
        """Set state for a view.
        
        Args:
            view_name: Name of the view.
            state: State dictionary to save.
        """
        self._view_states[view_name] = state
        self.view_state_changed.emit(view_name, state)
    
    def get_current_view(self) -> str:
        """Get the current view name.
        
        Returns:
            Current view name.
        """
        return self._view_manager.get_current_view()
    
    def _on_view_changed(self, view_name: str) -> None:
        """Handle view change from ViewManager.
        
        Args:
            view_name: Name of the view that was changed to.
        """
        self.view_changed.emit(view_name)
