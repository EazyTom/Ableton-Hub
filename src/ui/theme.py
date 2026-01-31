"""Theme system for Ableton Hub with multiple color schemes."""

from typing import Optional, Dict
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt


class ThemeColors:
    """Base color scheme definitions."""
    
    # Orange theme (Ableton default)
    ORANGE = {
        "background": "#1e1e1e",
        "background_alt": "#252525",
        "surface": "#2d2d2d",
        "surface_light": "#383838",
        "surface_hover": "#404040",
        "accent": "#ff764d",  # Ableton orange
        "accent_hover": "#ff8a66",
        "accent_pressed": "#e66a45",
        "text_primary": "#e0e0e0",
        "text_secondary": "#999999",
        "text_disabled": "#666666",
        "text_on_accent": "#ffffff",
        "border": "#3d3d3d",
        "border_light": "#4a4a4a",
        "border_focus": "#ff764d",
        "success": "#7cb342",
        "warning": "#ffa726",
        "error": "#ef5350",
        "info": "#42a5f5",
        "local": "#7cb342",
        "network": "#42a5f5",
        "cloud": "#ab47bc",
        "offline": "#666666",
        "selection": "#ff764d40",
        "selection_inactive": "#404040",
        "scrollbar": "#4a4a4a",
        "scrollbar_hover": "#5a5a5a",
    }
    
    # Blue theme
    BLUE = {
        "background": "#1a1f2e",
        "background_alt": "#222836",
        "surface": "#2a3441",
        "surface_light": "#353f4f",
        "surface_hover": "#3d4858",
        "accent": "#4fc3f7",  # Cool blue
        "accent_hover": "#66d0f9",
        "accent_pressed": "#3ab5e0",
        "text_primary": "#e0e8f5",
        "text_secondary": "#9db3d0",
        "text_disabled": "#6b7a8f",
        "text_on_accent": "#0a1929",
        "border": "#3a4555",
        "border_light": "#475263",
        "border_focus": "#4fc3f7",
        "success": "#66bb6a",
        "warning": "#ffb74d",
        "error": "#ef5350",
        "info": "#42a5f5",
        "local": "#66bb6a",
        "network": "#42a5f5",
        "cloud": "#ab47bc",
        "offline": "#6b7a8f",
        "selection": "#4fc3f740",
        "selection_inactive": "#3d4858",
        "scrollbar": "#475263",
        "scrollbar_hover": "#556373",
    }
    
    # Green theme
    GREEN = {
        "background": "#1e241e",
        "background_alt": "#252b25",
        "surface": "#2d352d",
        "surface_light": "#384238",
        "surface_hover": "#404a40",
        "accent": "#66bb6a",  # Green
        "accent_hover": "#7cc87f",
        "accent_pressed": "#56a85a",
        "text_primary": "#e0f0e0",
        "text_secondary": "#99b399",
        "text_disabled": "#667a66",
        "text_on_accent": "#0a1a0a",
        "border": "#3d4a3d",
        "border_light": "#4a5a4a",
        "border_focus": "#66bb6a",
        "success": "#81c784",
        "warning": "#ffb74d",
        "error": "#ef5350",
        "info": "#42a5f5",
        "local": "#81c784",
        "network": "#42a5f5",
        "cloud": "#ab47bc",
        "offline": "#667a66",
        "selection": "#66bb6a40",
        "selection_inactive": "#404a40",
        "scrollbar": "#4a5a4a",
        "scrollbar_hover": "#5a6a5a",
    }
    
    # Pink theme (vibrant pink accent)
    PINK = {
        "background": "#1a1a1a",
        "background_alt": "#222222",
        "surface": "#2a2a2a",
        "surface_light": "#353535",
        "surface_hover": "#3d3d3d",
        "accent": "#ff6b9d",  # Pink/magenta as primary accent
        "accent_hover": "#ff8bb3",
        "accent_pressed": "#e04b7d",
        "text_primary": "#f0f0f0",
        "text_secondary": "#b0b0b0",
        "text_disabled": "#707070",
        "text_on_accent": "#ffffff",
        "border": "#3d3d3d",
        "border_light": "#4a4a4a",
        "border_focus": "#ff6b9d",
        "success": "#4caf50",  # Bright green
        "warning": "#ffc107",  # Amber
        "error": "#f44336",    # Red
        "info": "#2196f3",      # Blue
        "local": "#4caf50",
        "network": "#2196f3",
        "cloud": "#9c27b0",     # Purple
        "offline": "#707070",
        "selection": "#ff6b9d40",
        "selection_inactive": "#3d3d3d",
        "scrollbar": "#4a4a4a",
        "scrollbar_hover": "#5a5a5a",
    }


class AbletonTheme:
    """Theme manager with support for multiple color schemes."""
    
    THEMES = {
        "orange": ThemeColors.ORANGE,
        "blue": ThemeColors.BLUE,
        "green": ThemeColors.GREEN,
        "pink": ThemeColors.PINK,
        # Legacy aliases for backward compatibility
        "cool_blue": ThemeColors.BLUE,
        "rainbow": ThemeColors.PINK,
    }
    
    THEME_NAMES = {
        "orange": "Orange (Ableton)",
        "blue": "Blue",
        "green": "Green",
        "pink": "Pink",
    }
    
    # Backward compatibility: class-level COLORS points to default theme
    COLORS = THEMES["orange"]
    
    # Font settings (shared across all themes)
    FONTS = {
        "family": "Segoe UI, SF Pro Display, -apple-system, sans-serif",
        "size_small": 11,
        "size_normal": 12,
        "size_large": 14,
        "size_title": 18,
        "size_header": 24,
    }
    
    def __init__(self, theme_name: str = "orange"):
        """Initialize the theme.
        
        Args:
            theme_name: Name of the theme to use ("orange", "blue", "green", "pink").
        """
        self.theme_name = theme_name
        self.COLORS = self.THEMES.get(theme_name, self.THEMES["orange"])
        self._stylesheet: str = ""
        self._build_stylesheet()
    
    @classmethod
    def get_available_themes(cls) -> Dict[str, str]:
        """Get available theme names and display names.
        
        Returns:
            Dictionary mapping theme IDs to display names.
        """
        return cls.THEME_NAMES.copy()
    
    @classmethod
    def get_color(cls, name: str, theme_name: Optional[str] = None) -> str:
        """Get a color value by name.
        
        Args:
            name: Color name from COLORS dict.
            theme_name: Optional theme name, uses default if not provided.
            
        Returns:
            Hex color string.
        """
        if theme_name:
            colors = cls.THEMES.get(theme_name, cls.THEMES["orange"])
        else:
            colors = cls.THEMES["orange"]
        return colors.get(name, "#ffffff")
    
    @classmethod
    def get_qcolor(cls, name: str, theme_name: Optional[str] = None) -> QColor:
        """Get a QColor by name.
        
        Args:
            name: Color name from COLORS dict.
            theme_name: Optional theme name, uses default if not provided.
            
        Returns:
            QColor object.
        """
        return QColor(cls.get_color(name, theme_name))
    
    def apply(self, app: QApplication) -> None:
        """Apply the theme to the application.
        
        Args:
            app: QApplication instance.
        """
        # Set the palette
        palette = self._create_palette()
        app.setPalette(palette)
        
        # Set the stylesheet
        app.setStyleSheet(self._stylesheet)
        
        # Set default font
        font_family = self.FONTS["family"].split(",")[0].strip()
        font = QFont(font_family)
        if font.pointSize() <= 0:
            font = QFont()
        
        if font.pointSize() > 0 or font.pixelSize() > 0:
            try:
                font.setPointSize(self.FONTS["size_normal"])
                if font.pointSize() <= 0:
                    font.setPixelSize(12)
            except (ValueError, TypeError):
                font.setPixelSize(12)
        else:
            font.setPixelSize(12)
        app.setFont(font)
    
    def _create_palette(self) -> QPalette:
        """Create a QPalette with the theme colors."""
        palette = QPalette()
        c = self.COLORS
        
        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(c["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text_primary"]))
        
        # Base colors (for inputs, lists)
        palette.setColor(QPalette.ColorRole.Base, QColor(c["surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c["surface_light"]))
        
        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(c["text_primary"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(c["text_disabled"]))
        
        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(c["surface"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text_primary"]))
        
        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(c["accent"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(c["text_on_accent"]))
        
        # Tool tips
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(c["surface_light"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(c["text_primary"]))
        
        # Links
        palette.setColor(QPalette.ColorRole.Link, QColor(c["accent"]))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(c["accent_pressed"]))
        
        return palette
    
    def _build_stylesheet(self) -> None:
        """Build the complete QSS stylesheet."""
        c = self.COLORS
        f = self.FONTS
        
        self._stylesheet = f"""
        /* Global styles */
        QWidget {{
            background-color: {c['background']};
            color: {c['text_primary']};
            font-family: {f['family']};
            font-size: {f['size_normal']}px;
        }}
        
        /* Main window */
        QMainWindow {{
            background-color: {c['background']};
        }}
        
        QMainWindow::separator {{
            background-color: {c['border']};
            width: 1px;
            height: 1px;
        }}
        
        /* Menu bar */
        QMenuBar {{
            background-color: {c['background']};
            color: {c['text_primary']};
            padding: 4px;
            border-bottom: 1px solid {c['border']};
        }}
        
        QMenuBar::item {{
            background: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {c['surface_hover']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {c['accent']};
            color: {c['text_on_accent']};
        }}
        
        /* Menus */
        QMenu {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 32px 8px 16px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {c['accent']};
            color: {c['text_on_accent']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {c['border']};
            margin: 4px 8px;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {c['surface']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 16px;
            min-width: 80px;
        }}
        
        QPushButton:hover {{
            background-color: {c['surface_hover']};
            border-color: {c['border_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {c['surface_light']};
        }}
        
        QPushButton:disabled {{
            background-color: {c['background']};
            color: {c['text_disabled']};
            border-color: {c['border']};
        }}
        
        QPushButton#primary {{
            background-color: {c['accent']};
            color: {c['text_on_accent']};
            border: none;
        }}
        
        QPushButton#primary:hover {{
            background-color: {c['accent_hover']};
        }}
        
        QPushButton#primary:pressed {{
            background-color: {c['accent_pressed']};
        }}
        
        /* Toolbar */
        QToolBar {{
            background-color: {c['background']};
            border: none;
            border-bottom: 1px solid {c['border']};
            spacing: 4px;
            padding: 4px;
        }}
        
        QToolBar::separator {{
            background-color: {c['border']};
            width: 1px;
            margin: 4px 2px;
        }}
        
        /* Tool buttons */
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
        }}
        
        QToolButton:hover {{
            background-color: {c['surface_hover']};
        }}
        
        QToolButton:pressed {{
            background-color: {c['surface_light']};
        }}
        
        QToolButton:checked {{
            background-color: {c['accent']};
            color: {c['text_on_accent']};
        }}
        
        /* Input fields */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c['surface']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 12px;
            selection-background-color: {c['accent']};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c['accent']};
        }}
        
        QLineEdit:disabled {{
            background-color: {c['background']};
            color: {c['text_disabled']};
        }}
        
        /* Combo box */
        QComboBox {{
            background-color: {c['surface']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 12px;
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: {c['border_light']};
        }}
        
        QComboBox:focus {{
            border-color: {c['accent']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {c['text_secondary']};
            margin-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            selection-background-color: {c['accent']};
        }}
        
        /* Spin box */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c['surface']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 6px 8px;
        }}
        
        /* Tab widget */
        QTabWidget::pane {{
            border: 1px solid {c['border']};
            border-radius: 6px;
            background-color: {c['background']};
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: {c['surface']};
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 10px 20px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {c['background']};
            color: {c['accent']};
            border-bottom: 2px solid {c['accent']};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {c['surface_hover']};
            color: {c['text_primary']};
        }}
        
        /* Scroll areas */
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        
        QScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {c['background']};
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c['scrollbar']};
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c['scrollbar_hover']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar:horizontal {{
            background-color: {c['background']};
            height: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c['scrollbar']};
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {c['scrollbar_hover']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        
        /* List and tree views */
        QListView, QTreeView, QTableView {{
            background-color: {c['surface']};
            alternate-background-color: {c['surface_light']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            outline: none;
        }}
        
        QListView::item, QTreeView::item, QTableView::item {{
            padding: 8px;
            border-radius: 4px;
        }}
        
        QListView::item:hover, QTreeView::item:hover, QTableView::item:hover {{
            background-color: {c['surface_hover']};
        }}
        
        QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
            background-color: {c['accent']};
            color: {c['text_on_accent']};
        }}
        
        /* Headers */
        QHeaderView::section {{
            background-color: {c['surface']};
            color: {c['text_secondary']};
            border: none;
            border-right: 1px solid {c['border']};
            border-bottom: 1px solid {c['border']};
            padding: 8px 12px;
            font-weight: bold;
        }}
        
        QHeaderView::section:hover {{
            background-color: {c['surface_hover']};
            color: {c['text_primary']};
        }}
        
        /* Splitters */
        QSplitter::handle {{
            background-color: {c['border']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        
        /* Group box */
        QGroupBox {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            margin-top: 16px;
            padding: 16px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 16px;
            padding: 0 8px;
            color: {c['text_secondary']};
        }}
        
        /* Progress bar */
        QProgressBar {{
            background-color: {c['surface']};
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {c['accent']};
            border-radius: 4px;
        }}
        
        /* Status bar */
        QStatusBar {{
            background-color: {c['background_alt']};
            border-top: 1px solid {c['border']};
            padding: 4px;
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {c['surface_light']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        
        /* Checkbox */
        QCheckBox {{
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c['border']};
            border-radius: 4px;
            background-color: {c['surface']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {c['accent']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c['accent']};
            border-color: {c['accent']};
        }}
        
        /* Radio button */
        QRadioButton {{
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c['border']};
            border-radius: 9px;
            background-color: {c['surface']};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {c['accent']};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c['accent']};
            border-color: {c['accent']};
        }}
        
        /* Slider */
        QSlider::groove:horizontal {{
            background-color: {c['surface']};
            height: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {c['accent']};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: {c['accent_hover']};
        }}
        
        /* Dialog */
        QDialog {{
            background-color: {c['background']};
        }}
        
        /* Frame */
        QFrame[frameShape="4"] {{
            background-color: {c['border']};
            max-height: 1px;
        }}
        
        QFrame[frameShape="5"] {{
            background-color: {c['border']};
            max-width: 1px;
        }}
        
        /* Labels */
        QLabel {{
            color: {c['text_primary']};
            background-color: transparent;
        }}
        
        QLabel#secondary {{
            color: {c['text_secondary']};
        }}
        
        QLabel#title {{
            font-size: {f['size_title']}px;
            font-weight: bold;
        }}
        
        QLabel#header {{
            font-size: {f['size_header']}px;
            font-weight: bold;
        }}
        """
    
    @staticmethod
    def safe_font_modify(font: QFont, point_size: Optional[int] = None, 
                         pixel_size: Optional[int] = None, bold: bool = False) -> QFont:
        """Safely modify a font, handling invalid point sizes.
        
        Args:
            font: The font to modify.
            point_size: Optional point size to set.
            pixel_size: Optional pixel size to set (used if point_size is invalid).
            bold: Whether to make the font bold.
            
        Returns:
            Modified QFont object.
        """
        if bold:
            font.setBold(True)
        
        if point_size is not None:
            if font.pointSize() > 0:
                try:
                    font.setPointSize(point_size)
                    if font.pointSize() <= 0:
                        if pixel_size is None:
                            pixel_size = int(point_size * 1.33)
                        font.setPixelSize(pixel_size)
                except (ValueError, TypeError):
                    if pixel_size is None:
                        pixel_size = int(point_size * 1.33)
                    font.setPixelSize(pixel_size)
            else:
                if pixel_size is None and point_size is not None:
                    pixel_size = int(point_size * 1.33)
                if pixel_size:
                    font.setPixelSize(pixel_size)
        elif pixel_size is not None:
            font.setPixelSize(pixel_size)
        
        return font
