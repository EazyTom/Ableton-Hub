"""View manager for handling view switching in MainWindow."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QWidget

from ...utils.logging import get_logger


class ViewManager(QObject):
    """Manages view switching and state in MainWindow.

    This class centralizes the logic for switching between different views
    in the main window's content stack, reducing complexity in MainWindow.
    """

    view_changed = pyqtSignal(str)  # View name

    # View name constants
    VIEW_PROJECTS = "projects"
    VIEW_COLLECTIONS = "collections"
    VIEW_LOCATIONS = "locations"
    VIEW_LINK = "link"
    VIEW_HEALTH = "health"
    VIEW_SIMILARITIES = "similarities"
    VIEW_PROPERTIES = "properties"
    VIEW_FIND_EXPORTS = "find_exports"

    def __init__(self, content_stack: QStackedWidget, parent: QObject | None = None):
        """Initialize the view manager.

        Args:
            content_stack: The QStackedWidget containing all views.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self._stack = content_stack
        self._current_view = self.VIEW_PROJECTS
        self._views: dict[str, QWidget] = {}  # name -> widget
        self._view_indices: dict[str, int] = {}  # name -> index

    def register_view(self, name: str, widget: QWidget, index: int) -> None:
        """Register a view widget with the manager.

        Args:
            name: View name (use class constants like VIEW_PROJECTS).
            widget: The widget to register.
            index: Index in the stacked widget.
        """
        self._views[name] = widget
        self._view_indices[name] = index
        self.logger.debug(f"Registered view '{name}' at index {index}")

    def switch_to_view(self, name: str) -> bool:
        """Switch to a named view.

        Args:
            name: View name to switch to.

        Returns:
            True if view was switched successfully, False otherwise.
        """
        if name not in self._views:
            self.logger.warning(f"Unknown view name: {name}")
            return False

        index = self._view_indices.get(name)
        if index is None or index < 0:
            self.logger.warning(f"Invalid index for view '{name}'")
            return False

        # Check if index is within bounds
        if index >= self._stack.count():
            self.logger.warning(
                f"Index {index} out of bounds for view '{name}' (stack has {self._stack.count()} items)"
            )
            return False

        self._stack.setCurrentIndex(index)
        self._current_view = name
        self.view_changed.emit(name)
        self.logger.debug(f"Switched to view '{name}' (index {index})")
        return True

    def get_current_view(self) -> str:
        """Get the current view name.

        Returns:
            Current view name.
        """
        return self._current_view

    def get_view_widget(self, name: str) -> QWidget | None:
        """Get a view widget by name.

        Args:
            name: View name.

        Returns:
            Widget if found, None otherwise.
        """
        return self._views.get(name)

    def get_current_index(self) -> int:
        """Get the current view index.

        Returns:
            Current index in the stacked widget.
        """
        return self._stack.currentIndex()

    def is_view_registered(self, name: str) -> bool:
        """Check if a view is registered.

        Args:
            name: View name.

        Returns:
            True if view is registered.
        """
        return name in self._views
