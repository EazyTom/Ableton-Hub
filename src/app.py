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
        
        # Load configuration BEFORE setting up logging (needed for logging config)
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
        # Detect development mode
        is_dev_mode = __debug__ or os.getenv('ABLETON_HUB_DEBUG') == '1'
        
        # Setup logging with config
        # If dev mode and config level is ERROR (default), override to DEBUG
        if is_dev_mode and self.config.logging.level == "ERROR":
            # Create a temporary config with DEBUG level for dev mode
            from .config import LoggingConfig
            dev_logging_config = LoggingConfig(
                enabled=self.config.logging.enabled,
                level="DEBUG",  # Override to DEBUG in dev mode
                log_dir=self.config.logging.log_dir,
                max_bytes=self.config.logging.max_bytes,
                backup_count=self.config.logging.backup_count
            )
            setup_logging(config=dev_logging_config)
        else:
            setup_logging(config=self.config.logging)
        
        self.logger = get_logger(__name__)
        
        # Install Qt message handler (routes through Python logging)
        self._install_qt_message_handler()
        
        # Install global exception handler
        self._install_exception_handler()
        
        # Set application icon
        self._set_application_icon()
    
    def _install_qt_message_handler(self) -> None:
        """Install a Qt message handler that routes messages through Python logging."""
        qt_logger = get_logger('PyQt6')
        
        def qt_message_handler(msg_type, context, message):
            """Route Qt messages through Python logging."""
            # Suppress QtDebugMsg (0) and QtInfoMsg (4) messages unless in dev mode
            is_dev_mode = __debug__ or os.getenv('ABLETON_HUB_DEBUG') == '1'
            
            if msg_type == QtMsgType.QtDebugMsg:
                if is_dev_mode:
                    qt_logger.debug(f"Qt Debug: {message}")
                return
            
            if msg_type == QtMsgType.QtInfoMsg:
                if is_dev_mode:
                    qt_logger.info(f"Qt Info: {message}")
                return
            
            # Route warnings and critical errors through Python logging
            if msg_type == QtMsgType.QtWarningMsg:
                qt_logger.warning(f"Qt Warning: {message}")
            elif msg_type == QtMsgType.QtCriticalMsg:
                qt_logger.error(f"Qt Critical: {message}")
            elif msg_type == QtMsgType.QtFatalMsg:
                qt_logger.critical(f"Qt Fatal: {message}")
        
        qInstallMessageHandler(qt_message_handler)
    
    def _install_exception_handler(self) -> None:
        """Install global exception handler for unhandled exceptions."""
        def exception_handler(exc_type, exc_value, exc_traceback):
            """Handle unhandled exceptions."""
            if issubclass(exc_type, KeyboardInterrupt):
                # Allow keyboard interrupts to work normally
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Log the exception with full traceback
            logger = get_logger(__name__)
            logger.critical(
                "Unhandled exception",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
            # Also show user-friendly message if possible
            try:
                if hasattr(self, 'app') and self.app:
                    from PyQt6.QtWidgets import QMessageBox
                    import traceback
                    msg = QMessageBox()
                    msg.setWindowTitle("Application Error")
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setText(
                        "An unexpected error occurred. Please check the log file for details.\n\n"
                        f"Error: {exc_type.__name__}: {exc_value}"
                    )
                    traceback_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                    msg.setDetailedText(f"Traceback:\n{traceback_str}")
                    msg.exec()
            except Exception:
                # If we can't show dialog, just log it
                pass
        
        sys.excepthook = exception_handler
        
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
            import sys
            resources = get_resources_path()
            
            # Try icons in order of preference (PNG works on all platforms)
            if sys.platform == "win32":
                icon_paths = [
                    resources / "icons" / "AProject.ico",
                    resources / "images" / "als-icon.png",
                ]
            else:
                # macOS/Linux - prefer PNG
                icon_paths = [
                    resources / "images" / "als-icon.png",
                    resources / "icons" / "AProject.ico",
                ]
            
            for icon_path in icon_paths:
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        self.app.setWindowIcon(icon)
                        self.logger.info(f"Set application icon from: {icon_path}")
                        return
            
            self.logger.warning("No valid application icon found")
        except Exception as e:
            self.logger.error(f"Failed to set application icon: {e}", exc_info=True)