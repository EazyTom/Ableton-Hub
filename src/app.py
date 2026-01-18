"""Main application class for Ableton Hub."""

import sys
import os
import logging
from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, qInstallMessageHandler, QtMsgType
from PyQt6.QtGui import QFont, QFontDatabase, QIcon

from . import __version__
from .config import get_config_manager, save_config
from .database import init_database
from .ui.main_window import MainWindow
from .ui.theme import AbletonTheme
from .utils.paths import get_resources_path
from .utils.logging import setup_logging, get_logger


class AbletonHubApp:
    """Main application controller for Ableton Hub."""
    
    def __init__(self, argv: list):
        """Initialize the application.
        
        Args:
            argv: Command line arguments.
        """
        # Enable high DPI scaling
        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
        self.app = QApplication(argv)
        self.app.setApplicationName("Ableton Hub")
        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("AbletonHub")
        self.app.setOrganizationDomain("abletonhub.local")
        
        # Setup logging
        setup_logging(log_level=logging.INFO, log_to_file=False)
        self.logger = get_logger(__name__)
        
        # Set application icon
        self._set_application_icon()
        
        # Load configuration
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
        # Initialize database
        init_database()
        
        # Apply theme (from config or default to orange)
        theme_name = getattr(self.config.ui, 'theme', 'orange')
        if theme_name == "dark":  # Legacy support
            theme_name = "orange"
        self.theme = AbletonTheme(theme_name)
        self.theme.apply(self.app)
        
        # Create main window
        self.main_window: Optional[MainWindow] = None
        self._cleanup_done = False
    
    def run(self) -> int:
        """Run the application event loop.
        
        Returns:
            Exit code from the application.
        """
        # Create and show main window
        self.main_window = MainWindow(self.config, self.theme)
        
        # Restore window geometry
        self._restore_window_state()
        
        self.main_window.show()
        
        # Mark first run as complete
        if self.config.first_run:
            self.config.first_run = False
            save_config()
        
        # Connect cleanup on exit
        self.app.aboutToQuit.connect(self._on_quit)
        
        # Start the event loop
        return self.app.exec()
    
    def _restore_window_state(self) -> None:
        """Restore window geometry from saved configuration."""
        if self.main_window is None:
            return
        
        wc = self.config.window
        
        # Set window size
        self.main_window.resize(wc.width, wc.height)
        
        # Set window position if saved
        if wc.x is not None and wc.y is not None:
            self.main_window.move(wc.x, wc.y)
        else:
            # Center on screen
            screen = self.app.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = (geometry.width() - wc.width) // 2
                y = (geometry.height() - wc.height) // 2
                self.main_window.move(x, y)
        
        # Maximize if was maximized
        if wc.maximized:
            self.main_window.showMaximized()
    
    def _save_window_state(self) -> None:
        """Save window geometry to configuration."""
        if self.main_window is None:
            return
        
        wc = self.config.window
        
        # Save maximized state
        wc.maximized = self.main_window.isMaximized()
        
        # Save geometry only if not maximized
        if not wc.maximized:
            geometry = self.main_window.geometry()
            wc.width = geometry.width()
            wc.height = geometry.height()
            wc.x = geometry.x()
            wc.y = geometry.y()
        
        # Save sidebar state from main window
        if hasattr(self.main_window, 'sidebar'):
            wc.sidebar_width = self.main_window.sidebar.width()
            wc.sidebar_collapsed = self.main_window.sidebar.isHidden()
        
        save_config()
    
    def _on_quit(self) -> None:
        """Handle application quit - save state and cleanup."""
        # Only run cleanup once
        if hasattr(self, '_cleanup_done') and self._cleanup_done:
            return
        
        self._cleanup_done = True
        
        try:
            self._save_window_state()
        except Exception:
            pass  # Ignore errors during shutdown
        
        # Stop any background services
        if self.main_window:
            try:
                self.main_window.cleanup()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Close database connections (non-blocking)
        try:
            from .database import close_database
            close_database()
        except Exception:
            pass  # Ignore errors closing database
    
    def _set_application_icon(self) -> None:
        """Set the application icon from resources."""
        try:
            icon_path = get_resources_path() / "images" / "AProject.ico"
            if not icon_path.exists():
                # Fallback to png if ico not found
                icon_path = get_resources_path() / "images" / "ableton-logo.png"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                # Set icon on the application
                self.app.setWindowIcon(icon)
                # Also set the application icon property (for taskbar/system tray)
                if hasattr(self.app, 'setApplicationIcon'):
                    # Some platforms may need this
                    pass
                self.logger.info(f"Set application icon from: {icon_path}")
                self.logger.debug(f"Icon isNull: {icon.isNull()}, availableSizes: {icon.availableSizes()}")
            else:
                self.logger.warning(f"Application icon not found at: {icon_path}")
        except Exception as e:
            self.logger.error(f"Failed to set application icon: {e}", exc_info=True)