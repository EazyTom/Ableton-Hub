"""SQLAlchemy ORM models for Ableton Hub."""

import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class LocationType(StrEnum):
    """Types of project locations."""

    LOCAL = "local"
    NETWORK = "network"
    DROPBOX = "dropbox"
    CLOUD = "cloud"
    COLLAB = "collab"
    USB = "usb"
    CUSTOM = "custom"


class ProjectStatus(StrEnum):
    """Project synchronization status."""

    LOCAL = "local"
    REMOTE = "remote"
    SYNCING = "syncing"
    MISSING = "missing"
    OFFLINE = "offline"


class CollectionType(StrEnum):
    """Types of project collections."""

    ALBUM = "album"
    EP = "ep"
    SINGLE = "single"
    COMPILATION = "compilation"
    SESSION = "session"
    CLIENT = "client"
    CUSTOM = "custom"


class Location(Base):
    """Represents a folder location containing Ableton projects."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    path = Column(String(1024), nullable=False, unique=True)
    location_type = Column(SQLEnum(LocationType), default=LocationType.LOCAL)
    is_active = Column(Boolean, default=True)
    is_favorite = Column(Boolean, default=False)
    last_scan_time = Column(DateTime, nullable=True)
    scan_frequency_hours = Column(Integer, default=24)
    credentials = Column(Text, nullable=True)  # Encrypted if needed
    icon = Column(String(64), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color like #FF764D
    sort_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))
    modified_date = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    projects = relationship("Project", back_populates="location", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}', path='{self.path}')>"


class Tag(Base):
    """Represents a tag for categorizing projects."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), nullable=False, default="#999999")  # Hex color
    category = Column(String(100), nullable=True)
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    project_tags = relationship("ProjectTag", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"


class ProjectTag(Base):
    """Junction table for many-to-many relationship between projects and tags."""

    __tablename__ = "project_tags"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    project = relationship("Project", back_populates="project_tags")
    tag = relationship("Tag", back_populates="project_tags")

    __table_args__ = (
        UniqueConstraint("project_id", "tag_id", name="unique_project_tag"),
        Index("idx_project_tags_project", "project_id"),
        Index("idx_project_tags_tag", "tag_id"),
    )

    def __repr__(self) -> str:
        return f"<ProjectTag(project_id={self.project_id}, tag_id={self.tag_id})>"


class Collection(Base):
    """Represents a collection/album of projects."""

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    artist_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    collection_type = Column(SQLEnum(CollectionType), default=CollectionType.ALBUM)
    artwork_path = Column(String(1024), nullable=True)
    release_date = Column(DateTime, nullable=True)
    color = Column(String(7), nullable=True)
    sort_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))
    modified_date = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Smart Collection fields
    is_smart = Column(Boolean, default=False)  # True if this is a smart collection
    smart_rules = Column(JSON, nullable=True)  # Filter criteria for smart collections

    # Relationships
    project_collections = relationship(
        "ProjectCollection", back_populates="collection", cascade="all, delete-orphan"
    )

    @property
    def projects(self) -> list["Project"]:
        """Get all projects in this collection, ordered by track number."""
        return [
            pc.project
            for pc in sorted(
                self.project_collections, key=lambda x: (x.disc_number or 1, x.track_number or 999)
            )
        ]

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}', type={self.collection_type})>"


class Project(Base):
    """Represents an Ableton Live project (.als file)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False, unique=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # File metadata
    file_size = Column(Integer, default=0)  # Bytes
    file_hash = Column(String(64), nullable=True)  # MD5/SHA256 hash for duplicate detection
    created_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    last_scanned = Column(DateTime, default=lambda: datetime.now(UTC))

    # Preview/Thumbnail
    thumbnail_path = Column(String(1024), nullable=True)  # Path to generated thumbnail
    preview_audio_path = Column(String(1024), nullable=True)  # Path to preview audio clip

    # Status
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.LOCAL)
    is_favorite = Column(Boolean, default=False)

    # User metadata
    export_song_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # List of tag IDs (DEPRECATED: Use project_tags relationship)
    custom_metadata = Column(JSON, default=dict)

    # Rating (1-5)
    rating = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)", name="check_rating_range"
        ),
        CheckConstraint("tempo IS NULL OR (tempo > 0 AND tempo < 1000)", name="check_tempo_range"),
        CheckConstraint("file_size >= 0", name="check_file_size"),
    )

    # Color coding
    color = Column(String(7), nullable=True)

    # Project metadata (extracted from .als file)
    plugins = Column(JSON, default=list)  # List of plugin names/paths
    devices = Column(JSON, default=list)  # List of Ableton device names
    tempo = Column(Float, nullable=True)  # Project tempo in BPM
    time_signature = Column(String(10), nullable=True)  # e.g., "4/4", "3/4"
    track_count = Column(Integer, default=0)  # Total tracks
    audio_tracks = Column(Integer, default=0)  # Audio track count
    midi_tracks = Column(Integer, default=0)  # MIDI track count
    return_tracks = Column(Integer, default=0)  # Return track count
    has_master_track = Column(Boolean, default=True)  # Has master track
    arrangement_length = Column(Float, nullable=True)  # Length in bars
    arrangement_duration_seconds = Column(
        Float, nullable=True
    )  # Calculated duration in seconds (bars * 4 / tempo * 60)
    ableton_version = Column(String(50), nullable=True)  # Version that created the set
    sample_references = Column(JSON, default=list)  # List of sample file paths
    has_automation = Column(Boolean, default=False)  # Has automation data
    last_parsed = Column(DateTime, nullable=True)  # When metadata was last extracted

    # Musical key/scale information
    musical_key = Column(String(10), nullable=True)  # Root note (e.g., "C", "D#", "A")
    scale_type = Column(String(50), nullable=True)  # Scale type (e.g., "Major", "Minor", "Dorian")
    is_in_key = Column(Boolean, nullable=True)  # Whether "In Key" mode is enabled

    # Timeline markers (extracted from .als files using dawtool)
    timeline_markers = Column(
        JSON, default=list
    )  # List of timeline markers: [{"time": float, "text": str}]

    # Relationships
    location = relationship("Location", back_populates="projects")
    project_collections = relationship(
        "ProjectCollection", back_populates="project", cascade="all, delete-orphan"
    )
    exports = relationship("Export", back_populates="project", cascade="all, delete-orphan")
    project_tags = relationship(
        "ProjectTag", back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def collections(self) -> list[Collection]:
        """Get all collections this project belongs to."""
        return [pc.collection for pc in self.project_collections]

    @property
    def tag_list(self) -> list[int]:
        """Get the list of tag IDs (from project_tags relationship)."""
        if self.project_tags:
            return [pt.tag_id for pt in self.project_tags]
        # Fallback to legacy JSON field for backward compatibility
        return self.tags or []

    @property
    def tag_objects(self) -> list["Tag"]:
        """Get the list of Tag objects."""
        return [pt.tag for pt in self.project_tags] if self.project_tags else []

    def get_plugins_list(self) -> list[str]:
        """Get plugins as a Python list."""
        if isinstance(self.plugins, str):
            return json.loads(self.plugins) if self.plugins else []
        return self.plugins or []

    def get_devices_list(self) -> list[str]:
        """Get devices as a Python list."""
        if isinstance(self.devices, str):
            return json.loads(self.devices) if self.devices else []
        return self.devices or []

    def get_key_display(self) -> str | None:
        """Get a formatted display string for musical key/scale.

        Returns:
            String like "C Major", "D# Minor", or None if not set.
        """
        if self.musical_key and self.scale_type:
            return f"{self.musical_key} {self.scale_type}"
        elif self.musical_key:
            return self.musical_key
        return None

    def get_live_version_major(self) -> int | None:
        """Extract major version number from ableton_version string.

        Returns:
            Major version number (9, 10, 11, 12) or None if not available.
        """
        if not self.ableton_version:
            return None

        # Parse version string like "Ableton Live 11.3.10" or "Live 12.0.5"
        match = re.search(r"Live\s+(\d+)", self.ableton_version)
        if match:
            try:
                major_version = int(match.group(1))
                if 9 <= major_version <= 12:
                    return major_version
            except (ValueError, TypeError):
                pass
        return None

    def get_live_version_display(self) -> str | None:
        """Get display string for Live version (v9, v10, v11, v12).

        Returns:
            Version string like "v11" or None if not available.
        """
        major = self.get_live_version_major()
        return f"v{major}" if major else None

    def get_sample_references_list(self) -> list[str]:
        """Get sample references as a Python list."""
        if isinstance(self.sample_references, str):
            return json.loads(self.sample_references) if self.sample_references else []
        return self.sample_references or []

    def get_timeline_markers_list(self) -> list[dict[str, Any]]:
        """Get timeline markers as a Python list.

        Returns:
            List of marker dicts with 'time' (float) and 'text' (str) keys.
        """
        if isinstance(self.timeline_markers, str):
            return json.loads(self.timeline_markers) if self.timeline_markers else []
        return self.timeline_markers or []

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


class ProjectCollection(Base):
    """Association table for many-to-many relationship between projects and collections."""

    __tablename__ = "project_collections"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    track_number = Column(Integer, nullable=True)
    disc_number = Column(Integer, default=1)
    is_bonus = Column(Boolean, default=False)
    track_name = Column(String(255), nullable=True)  # Track name specific to this collection
    track_artwork_path = Column(String(1024), nullable=True)  # Artwork for this track
    export_id = Column(
        Integer, ForeignKey("exports.id", ondelete="SET NULL"), nullable=True
    )  # Selected export for track name
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    project = relationship("Project", back_populates="project_collections")
    collection = relationship("Collection", back_populates="project_collections")
    export = relationship("Export", back_populates="project_collections")

    __table_args__ = (
        UniqueConstraint("project_id", "collection_id", name="unique_project_collection"),
        CheckConstraint("track_number IS NULL OR track_number > 0", name="check_track_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectCollection(project_id={self.project_id}, "
            f"collection_id={self.collection_id}, track={self.track_number})>"
        )


class Export(Base):
    """Represents an exported audio file from a project."""

    __tablename__ = "exports"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    export_path = Column(String(1024), nullable=False, unique=True)
    export_name = Column(String(255), nullable=False)
    export_date = Column(DateTime, nullable=True)

    # Audio metadata
    format = Column(String(10), nullable=True)  # wav, mp3, flac, aiff
    sample_rate = Column(Integer, nullable=True)
    bit_depth = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    file_size = Column(Integer, default=0)

    created_date = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    project = relationship("Project", back_populates="exports")
    project_collections = relationship("ProjectCollection", back_populates="export")

    def __repr__(self) -> str:
        return f"<Export(id={self.id}, name='{self.export_name}', project_id={self.project_id})>"


class LinkDevice(Base):
    """Represents a device discovered on the Ableton Link network."""

    __tablename__ = "link_devices"

    id = Column(Integer, primary_key=True)
    device_name = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv6 max length
    port = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(UTC))
    first_seen = Column(DateTime, default=lambda: datetime.now(UTC))

    # Device info
    device_type = Column(String(100), nullable=True)  # e.g., "Ableton Live", "iPad"
    session_count = Column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint("device_name", "ip_address", name="unique_device"),
        Index("idx_link_device_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<LinkDevice(id={self.id}, name='{self.device_name}', ip='{self.ip_address}')>"


class LiveInstallation(Base):
    """Represents a user-defined Ableton Live installation."""

    __tablename__ = "live_installations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Display name (e.g., "Live 11 Suite")
    version = Column(String(50), nullable=False)  # Version string (e.g., "11.3.13")
    executable_path = Column(String(1024), nullable=False, unique=True)  # Path to Live executable
    build = Column(String(50), nullable=True)  # Build number if available
    is_suite = Column(Boolean, default=False)  # True if Live Suite
    is_favorite = Column(Boolean, default=False)  # Favorite installation (used for double-click)
    is_auto_detected = Column(
        Boolean, default=False
    )  # True if auto-detected, False if manually added
    notes = Column(Text, nullable=True)  # User notes
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))
    modified_date = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def get_major_version(self) -> int | None:
        """Extract major version number from version string.

        Handles full version strings including hotfix and beta versions.
        Examples: "11.3.13" -> 11, "12.0.5" -> 12, "12.0.5b1" -> 12, "12b1" -> 12

        Returns:
            Major version number (9, 10, 11, 12) or None if not available.
        """
        if not self.version:
            return None

        # Parse version string like "11.3.13", "12.0.5", "12.0.5b1", or "12b1"
        # First, remove any beta/rc suffixes (e.g., "b1", "beta1", "rc2") from the first part
        # Split by dot to get parts
        version_parts = self.version.split(".")
        if version_parts:
            try:
                # Get the first part and remove any beta suffix (e.g., "12b1" -> "12")
                first_part = version_parts[0]
                # Remove any trailing letters and digits (beta suffixes)
                major_version_str = re.sub(r"[a-zA-Z].*$", "", first_part)
                major_version = int(major_version_str)
                if 9 <= major_version <= 12:
                    return major_version
            except (ValueError, TypeError):
                pass
        return None

    def __repr__(self) -> str:
        return f"<LiveInstallation(id={self.id}, name='{self.name}', version='{self.version}')>"


# Create indexes for common queries


class AppSettings(Base):
    """Application settings stored in the database."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), default="string")  # string, int, bool, json
    description = Column(Text, nullable=True)
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))
    modified_date = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    @classmethod
    def get_value(cls, session, key: str, default=None):
        """Get a setting value by key."""
        setting = session.query(cls).filter(cls.key == key).first()
        if not setting:
            return default

        if setting.value_type == "int":
            return int(setting.value) if setting.value else default
        elif setting.value_type == "bool":
            return setting.value.lower() in ("true", "1", "yes") if setting.value else default
        elif setting.value_type == "json":
            return json.loads(setting.value) if setting.value else default
        return setting.value

    @classmethod
    def set_value(
        cls, session, key: str, value, value_type: str = "string", description: str = None
    ):
        """Set a setting value."""
        setting = session.query(cls).filter(cls.key == key).first()
        if not setting:
            setting = cls(key=key, value_type=value_type, description=description)
            session.add(setting)

        if value_type == "json":
            setting.value = json.dumps(value)
        else:
            setting.value = str(value) if value is not None else None

        setting.value_type = value_type
        if description:
            setting.description = description

        session.commit()
        return setting

    def __repr__(self) -> str:
        return f"<AppSettings(key='{self.key}', value='{self.value}')>"


# Create indexes for common queries
Index("idx_project_location", Project.location_id)
Index("idx_live_installation_favorite", LiveInstallation.is_favorite)
Index("idx_project_name", Project.name)
Index("idx_project_modified", Project.modified_date)
Index("idx_project_favorite", Project.is_favorite)
Index("idx_location_active", Location.is_active)
Index("idx_export_project", Export.project_id)
Index("idx_app_settings_key", AppSettings.key)

# Composite indexes for common query patterns (Phase 1 & 2)
Index("idx_project_location_status", Project.location_id, Project.status)
Index("idx_project_favorite_modified", Project.is_favorite, Project.modified_date)
Index(
    "idx_project_collection_track", ProjectCollection.collection_id, ProjectCollection.track_number
)
Index("idx_export_project_date", Export.project_id, Export.export_date)
Index("idx_collection_type", Collection.collection_type)
Index("idx_project_rating", Project.rating)
