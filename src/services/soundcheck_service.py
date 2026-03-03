"""Soundcheck service - plays a startup sound to test audio output."""

from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .audio_player import AudioPlayer
from ..utils.logging import get_logger
from ..utils.paths import get_app_data_dir, get_resources_path

logger = get_logger(__name__)

# Playback timing
FADE_IN_MS = 600
FADE_OUT_MS = 1200  # Slow fade out for smooth ending
PLAY_DURATION_MS = 3000  # Full 3 seconds at target volume before fade out
FADE_STEP_MS = 50
TARGET_VOLUME = 0.25  # 25% volume for startup sound


def get_soundcheck_path(custom_path: str = "") -> Path:
    """Get the path to the soundcheck file.

    Args:
        custom_path: User-selected path from config; empty = use default.

    Returns:
        Path to the soundcheck file.
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
        logger.warning(f"Soundcheck path not found: {custom_path}, using default")

    return _ensure_default_soundcheck()


def _ensure_default_soundcheck() -> Path:
    """Ensure default soundcheck exists; prefer bundled soundcheck.mp3, else .ogg, else generate.

    Uses src/resources/sfx (works for source, pip install, and Briefcase packaged builds).

    Returns:
        Path to the soundcheck file (may not exist if generation fails).
    """
    for name in ("soundcheck.mp3", "soundcheck.ogg"):
        path = get_resources_path() / "sfx" / name
        if path.exists():
            return path

    # Try to generate - use app data dir (writable) when resources may be read-only
    app_data = get_app_data_dir()
    app_sfx_dir = app_data / "sfx"
    generated_path = app_sfx_dir / "soundcheck.ogg"

    if generated_path.exists():
        return generated_path

    try:
        import numpy as np
        import soundfile as sf

        app_sfx_dir.mkdir(parents=True, exist_ok=True)
        sample_rate = 44100
        duration_sec = 2.0
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=np.float32)
        # Gentle 440 Hz sine with soft envelope
        freq = 440.0
        y = 0.25 * np.sin(2 * np.pi * freq * t)
        # Fade in/out envelope
        fade_samples = int(0.1 * sample_rate)
        y[:fade_samples] *= np.linspace(0, 1, fade_samples)
        y[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        sf.write(str(generated_path), y, sample_rate, format="OGG")
        logger.info(f"Generated default soundcheck at {generated_path}")
        return generated_path
    except Exception as e:
        logger.warning(f"Could not generate soundcheck.ogg: {e}")
        return (
            get_resources_path() / "sfx" / "soundcheck.mp3"
        )  # Expected path even if generation failed


class SoundcheckService(QObject):
    """Plays a short soundcheck at startup to verify audio output."""

    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    playback_started = pyqtSignal(str)  # Display name of audio file playing

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._player = AudioPlayer.instance()
        self._fade_timer: QTimer | None = None
        self._fade_start_volume = 0.0
        self._fade_target_volume = 0.0
        self._fade_elapsed_ms = 0
        self._fade_duration_ms = 0

    def play_soundcheck(self, custom_path: str = "") -> None:
        """Start the soundcheck playback (fade in, 3s play, fade out).

        Args:
            custom_path: User-selected path from config; empty = use default soundcheck.ogg.
        """
        path = get_soundcheck_path(custom_path)
        if not path.exists():
            self.error_occurred.emit("Soundcheck file not found")
            self.finished.emit()
            return

        path_str = str(path)
        if not self._player.load(path_str):
            self.error_occurred.emit(f"Failed to load soundcheck: {path_str}")
            self.finished.emit()
            return

        self._player.volume = 0.0
        self._player.play(path_str)

        self.playback_started.emit(path.name)
        self._start_fade(FADE_IN_MS, 0.0, TARGET_VOLUME, self._on_fade_in_done)

    def _start_fade(
        self,
        duration_ms: int,
        start_vol: float,
        target_vol: float,
        on_done: Callable[[], None],
    ) -> None:
        """Start a volume fade."""
        self._fade_start_volume = start_vol
        self._fade_target_volume = target_vol
        self._fade_duration_ms = duration_ms
        self._fade_elapsed_ms = 0
        self._fade_on_done = on_done

        if self._fade_timer is None:
            self._fade_timer = QTimer(self)
            self._fade_timer.timeout.connect(self._on_fade_tick)
        self._fade_timer.start(FADE_STEP_MS)

    def _on_fade_tick(self) -> None:
        """Update volume during fade."""
        self._fade_elapsed_ms += FADE_STEP_MS
        if self._fade_elapsed_ms >= self._fade_duration_ms:
            if self._fade_timer:
                self._fade_timer.stop()
            self._player.volume = self._fade_target_volume
            self._fade_on_done()
            return

        t = self._fade_elapsed_ms / self._fade_duration_ms
        vol = self._fade_start_volume + t * (self._fade_target_volume - self._fade_start_volume)
        self._player.volume = vol

    def _on_fade_in_done(self) -> None:
        """Fade in complete; play full 3 seconds at target volume."""
        QTimer.singleShot(PLAY_DURATION_MS, self._on_play_duration_done)

    def _on_play_duration_done(self) -> None:
        """Full 3 seconds complete; start slow fade out."""
        self._start_fade(FADE_OUT_MS, TARGET_VOLUME, 0.0, self._on_fade_out_done)

    def _on_fade_out_done(self) -> None:
        """Fade out complete; stop and emit finished."""
        self._player.stop()
        self._player.volume = 0.7  # Restore default for normal playback
        self.finished.emit()
