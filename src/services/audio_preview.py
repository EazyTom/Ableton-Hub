"""Audio preview and thumbnail generation service."""

from typing import Optional, Literal
from pathlib import Path
import subprocess
import sys
import random

from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QLinearGradient
from PyQt6.QtCore import Qt

from ..database import get_session, Project, Export
from ..utils.paths import get_thumbnail_cache_dir
from ..config import get_config


class AudioPreviewGenerator:
    """Service for generating audio preview thumbnails."""
    
    # Color mode options
    COLOR_MODES = Literal["rainbow", "random", "accent"]
    
    @staticmethod
    def _get_project_color(project_id: int, color_mode: COLOR_MODES = "rainbow") -> Optional[QColor]:
        """Get a color for a project based on color mode.
        
        Args:
            project_id: Project ID for consistent random color generation.
            color_mode: Color mode ("rainbow", "random", or "accent").
            
        Returns:
            QColor or None for rainbow mode (which uses gradient).
        """
        if color_mode == "random":
            # Generate consistent random color based on project ID
            random.seed(project_id)
            r = random.randint(100, 255)
            g = random.randint(100, 255)
            b = random.randint(100, 255)
            random.seed()  # Reset seed
            return QColor(r, g, b)
        elif color_mode == "accent":
            return QColor(0, 200, 100)  # Green accent
        else:  # rainbow
            return None  # Rainbow uses gradient, not single color
    
    @staticmethod
    def _get_ffmpeg_colors(color_mode: COLOR_MODES = "rainbow") -> str:
        """Get ffmpeg color string based on color mode.
        
        Note: FFmpeg's showwavespic doesn't support gradient colors directly.
        For rainbow mode, we use a vibrant cyan/magenta color. The simple
        waveform fallback uses full rainbow gradient.
        
        Args:
            color_mode: Color mode ("rainbow", "random", or "accent").
            
        Returns:
            FFmpeg color string for showwavespic filter.
        """
        if color_mode == "rainbow":
            # Use vibrant cyan for rainbow mode (simple waveform fallback uses full gradient)
            return "0x00ffff"  # Cyan
        elif color_mode == "random":
            # For random, we'll use a single color generated per project
            # This will be handled in generate_waveform_image
            return "0x00ff00"  # Default, will be overridden
        else:  # accent
            return "0x00ff00"  # Green accent
    
    @staticmethod
    def has_ffmpeg() -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def generate_waveform_image(
        audio_path: str,
        output_path: str,
        width: int = 200,
        height: int = 60,
        color_mode: COLOR_MODES = "rainbow",
        project_id: Optional[int] = None
    ) -> bool:
        """Generate a waveform image from an audio file.
        
        Args:
            audio_path: Path to audio file.
            output_path: Path to save the waveform image.
            width: Image width in pixels.
            height: Image height in pixels.
            color_mode: Color mode ("rainbow", "random", or "accent").
            project_id: Project ID for consistent random color (required if color_mode="random").
            
        Returns:
            True if successful, False otherwise.
        """
        if not AudioPreviewGenerator.has_ffmpeg():
            return False
        
        try:
            audio_file = Path(audio_path)
            if not audio_file.exists():
                return False
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Get color string for ffmpeg
            if color_mode == "random" and project_id is not None:
                # Generate consistent random color for this project
                color = AudioPreviewGenerator._get_project_color(project_id, "random")
                color_hex = f"0x{color.red():02x}{color.green():02x}{color.blue():02x}"
            else:
                color_hex = AudioPreviewGenerator._get_ffmpeg_colors(color_mode)
            
            # Use ffmpeg to extract waveform data
            # For rainbow, use gradient colors; for others, use single color
            if color_mode == "rainbow":
                # Rainbow gradient: use multiple colors
                cmd = [
                    'ffmpeg',
                    '-i', str(audio_file),
                    '-filter_complex', f'[0:a]aformat=channel_layouts=mono,showwavespic=s={width}x{height}:colors={color_hex}',
                    '-frames:v', '1',
                    '-y',  # Overwrite output
                    str(output_file)
                ]
            else:
                # Single color (random or accent)
                cmd = [
                    'ffmpeg',
                    '-i', str(audio_file),
                    '-filter_complex', f'[0:a]aformat=channel_layouts=mono,showwavespic=s={width}x{height}:colors={color_hex}',
                    '-frames:v', '1',
                    '-y',  # Overwrite output
                    str(output_file)
                ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error generating waveform: {e}")
            return False
    
    @staticmethod
    def generate_simple_waveform(
        audio_path: str,
        width: int = 200,
        height: int = 60,
        color_mode: COLOR_MODES = "rainbow",
        project_id: Optional[int] = None
    ) -> Optional[QPixmap]:
        """Generate a simple waveform pixmap (fallback if ffmpeg not available).
        
        Args:
            audio_path: Path to audio file.
            width: Image width.
            height: Image height.
            color_mode: Color mode ("rainbow", "random", or "accent").
            project_id: Project ID for consistent random color (required if color_mode="random").
            
        Returns:
            QPixmap with waveform or None if failed.
        """
        # This is a placeholder - would need audio library like librosa
        # For now, return a simple placeholder
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(30, 30, 30))  # Dark background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_y = height // 2
        
        if color_mode == "rainbow":
            # Create rainbow gradient
            gradient = QLinearGradient(0, 0, width, 0)
            gradient.setColorAt(0.0, QColor(255, 0, 0))      # Red
            gradient.setColorAt(0.2, QColor(255, 136, 0))    # Orange
            gradient.setColorAt(0.4, QColor(255, 255, 0))    # Yellow
            gradient.setColorAt(0.6, QColor(0, 255, 0))     # Green
            gradient.setColorAt(0.8, QColor(0, 136, 255))   # Blue
            gradient.setColorAt(1.0, QColor(255, 0, 255))  # Purple
            painter.setPen(QPen(gradient, 2))
        elif color_mode == "random" and project_id is not None:
            # Use consistent random color for this project
            color = AudioPreviewGenerator._get_project_color(project_id, "random")
            painter.setPen(QPen(color, 2))
        else:
            # Accent color (green)
            painter.setPen(QPen(QColor(0, 200, 100), 2))
        
        # Draw simple placeholder waveform
        for x in range(0, width, 4):
            # Random height for demo (would use actual audio data)
            wave_height = random.randint(5, height // 2)
            painter.drawLine(x, center_y - wave_height, x, center_y + wave_height)
        
        painter.end()
        return pixmap
    
    @staticmethod
    def get_or_generate_preview(
        project_id: int,
        color_mode: Optional[COLOR_MODES] = None
    ) -> Optional[str]:
        """Get or generate preview thumbnail for a project.
        
        Args:
            project_id: ID of the project.
            color_mode: Color mode for waveform ("rainbow", "random", or "accent").
                        If None, uses config setting (defaults to "rainbow").
            
        Returns:
            Path to preview thumbnail, or None if unavailable.
        """
        # Get color mode from config if not specified
        if color_mode is None:
            config = get_config()
            color_mode = config.ui.waveform_color_mode  # type: ignore
        session = get_session()
        try:
            project = session.query(Project).get(project_id)
            if not project:
                return None
            
            # Check if preview already exists
            if project.thumbnail_path and Path(project.thumbnail_path).exists():
                return project.thumbnail_path
            
            # Try to find an export to generate preview from
            exports = session.query(Export).filter(
                Export.project_id == project_id
            ).order_by(Export.created_date.desc()).all()
            
            if not exports:
                return None
            
            # Use the most recent export
            export = exports[0]
            export_path = Path(export.export_path)
            
            if not export_path.exists():
                return None
            
            # Generate preview path using proper cache directory
            preview_dir = get_thumbnail_cache_dir()
            preview_path = preview_dir / f"project_{project_id}.png"
            
            # Generate waveform with color mode
            if AudioPreviewGenerator.generate_waveform_image(
                str(export_path),
                str(preview_path),
                color_mode=color_mode,
                project_id=project_id
            ):
                # Update project with preview path
                project.thumbnail_path = str(preview_path)
                session.commit()
                return str(preview_path)
            else:
                # Fallback to simple waveform
                pixmap = AudioPreviewGenerator.generate_simple_waveform(
                    str(export_path),
                    color_mode=color_mode,
                    project_id=project_id
                )
                if pixmap:
                    pixmap.save(str(preview_path))
                    project.thumbnail_path = str(preview_path)
                    session.commit()
                    return str(preview_path)
            
            return None
            
        finally:
            session.close()
