"""Database migration utilities for Ableton Hub."""

from typing import List, Callable
from sqlalchemy import text
from sqlalchemy.engine import Engine


def migration_add_track_fields(engine: Engine) -> None:
    """Add track_name and track_artwork_path columns to project_collections table."""
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text(
            "PRAGMA table_info(project_collections)"
        ))
        columns = [row[1] for row in result.fetchall()]
        
        if 'track_name' not in columns:
            conn.execute(text(
                "ALTER TABLE project_collections ADD COLUMN track_name TEXT"
            ))
        
        if 'track_artwork_path' not in columns:
            conn.execute(text(
                "ALTER TABLE project_collections ADD COLUMN track_artwork_path TEXT"
            ))
        
        conn.commit()


def migration_add_phase_25_fields(engine: Engine) -> None:
    """Add Phase 2.5 fields: smart collections, file_hash, preview fields."""
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(projects)"))
        project_columns = [row[1] for row in result.fetchall()]
        
        result = conn.execute(text("PRAGMA table_info(collections)"))
        collection_columns = [row[1] for row in result.fetchall()]
        
        # Add to projects table
        if 'file_hash' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN file_hash TEXT"
            ))
        
        if 'thumbnail_path' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN thumbnail_path TEXT"
            ))
        
        if 'preview_audio_path' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN preview_audio_path TEXT"
            ))
        
        # Add to collections table
        if 'is_smart' not in collection_columns:
            conn.execute(text(
                "ALTER TABLE collections ADD COLUMN is_smart INTEGER DEFAULT 0"
            ))
        
        if 'smart_rules' not in collection_columns:
            conn.execute(text(
                "ALTER TABLE collections ADD COLUMN smart_rules TEXT"
            ))
        
        conn.commit()


def migration_add_project_metadata_fields(engine: Engine) -> None:
    """Add project metadata fields extracted from .als files."""
    import json
    from datetime import datetime
    
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(projects)"))
        project_columns = [row[1] for row in result.fetchall()]
        
        # Add plugin and device fields
        if 'plugins' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN plugins TEXT DEFAULT '[]'"
            ))
        
        if 'devices' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN devices TEXT DEFAULT '[]'"
            ))
        
        if 'tempo' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN tempo REAL"
            ))
        
        if 'time_signature' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN time_signature TEXT"
            ))
        
        if 'track_count' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN track_count INTEGER DEFAULT 0"
            ))
        
        if 'audio_tracks' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN audio_tracks INTEGER DEFAULT 0"
            ))
        
        if 'midi_tracks' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN midi_tracks INTEGER DEFAULT 0"
            ))
        
        if 'return_tracks' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN return_tracks INTEGER DEFAULT 0"
            ))
        
        if 'has_master_track' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN has_master_track INTEGER DEFAULT 1"
            ))
        
        if 'arrangement_length' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN arrangement_length REAL"
            ))
        
        if 'ableton_version' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN ableton_version TEXT"
            ))
        
        if 'sample_references' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN sample_references TEXT DEFAULT '[]'"
            ))
        
        if 'has_automation' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN has_automation INTEGER DEFAULT 0"
            ))
        
        if 'last_parsed' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN last_parsed TEXT"
            ))
        
        conn.commit()


def migration_update_fts_for_plugins(engine: Engine) -> None:
    """Update FTS table to include plugins and devices fields."""
    with engine.connect() as conn:
        # Check if FTS table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects_fts'"
        ))
        
        if result.fetchone() is not None:
            # Check if plugins/devices columns exist in FTS
            result = conn.execute(text("PRAGMA table_info(projects_fts)"))
            fts_columns = [row[1] for row in result.fetchall()]
            
            # If FTS table exists but doesn't have plugins/devices, we need to recreate it
            if 'plugins' not in fts_columns or 'devices' not in fts_columns:
                # Drop old FTS table and triggers
                conn.execute(text("DROP TABLE IF EXISTS projects_fts"))
                conn.execute(text("DROP TRIGGER IF EXISTS projects_ai"))
                conn.execute(text("DROP TRIGGER IF EXISTS projects_ad"))
                conn.execute(text("DROP TRIGGER IF EXISTS projects_au"))
                
                # Recreate FTS table with plugins and devices
                conn.execute(text("""
                    CREATE VIRTUAL TABLE projects_fts USING fts5(
                        name,
                        export_song_name,
                        notes,
                        tags,
                        plugins,
                        devices,
                        content='projects',
                        content_rowid='id'
                    )
                """))
                
                # Recreate triggers with plugins and devices
                conn.execute(text("""
                    CREATE TRIGGER projects_ai AFTER INSERT ON projects BEGIN
                        INSERT INTO projects_fts(rowid, name, export_song_name, notes, tags, plugins, devices)
                        VALUES (
                            new.id, 
                            new.name, 
                            new.export_song_name, 
                            new.notes, 
                            new.tags,
                            COALESCE(new.plugins, '[]'),
                            COALESCE(new.devices, '[]')
                        );
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER projects_ad AFTER DELETE ON projects BEGIN
                        INSERT INTO projects_fts(projects_fts, rowid, name, export_song_name, notes, tags, plugins, devices)
                        VALUES ('delete', old.id, old.name, old.export_song_name, old.notes, old.tags, COALESCE(old.plugins, '[]'), COALESCE(old.devices, '[]'));
                    END
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER projects_au AFTER UPDATE ON projects BEGIN
                        INSERT INTO projects_fts(projects_fts, rowid, name, export_song_name, notes, tags, plugins, devices)
                        VALUES ('delete', old.id, old.name, old.export_song_name, old.notes, old.tags, COALESCE(old.plugins, '[]'), COALESCE(old.devices, '[]'));
                        INSERT INTO projects_fts(rowid, name, export_song_name, notes, tags, plugins, devices)
                        VALUES (
                            new.id, 
                            new.name, 
                            new.export_song_name, 
                            new.notes, 
                            new.tags,
                            COALESCE(new.plugins, '[]'),
                            COALESCE(new.devices, '[]')
                        );
                    END
                """))
                
                # Rebuild FTS index from existing projects
                conn.execute(text("""
                    INSERT INTO projects_fts(rowid, name, export_song_name, notes, tags, plugins, devices)
                    SELECT id, name, export_song_name, notes, tags, COALESCE(plugins, '[]'), COALESCE(devices, '[]')
                    FROM projects
                """))
                
                conn.commit()


def migration_add_arrangement_duration(engine: Engine) -> None:
    """Add arrangement_duration_seconds column to projects table."""
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(projects)"))
        project_columns = [row[1] for row in result.fetchall()]
        
        if 'arrangement_duration_seconds' not in project_columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN arrangement_duration_seconds REAL"
            ))
            conn.commit()
            
            # Calculate duration for existing projects that have bars and tempo
            conn.execute(text("""
                UPDATE projects 
                SET arrangement_duration_seconds = (arrangement_length * 4.0 / tempo) * 60.0
                WHERE arrangement_length IS NOT NULL 
                  AND arrangement_length > 0 
                  AND tempo IS NOT NULL 
                  AND tempo > 0
            """))
            conn.commit()


def migration_add_live_installations(engine: Engine) -> None:
    """Add live_installations table for storing Live installations."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='live_installations'"
        ))
        if result.fetchone() is not None:
            return  # Table already exists
        
        # Create live_installations table
        conn.execute(text("""
            CREATE TABLE live_installations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                version VARCHAR(50) NOT NULL,
                executable_path VARCHAR(1024) NOT NULL UNIQUE,
                build VARCHAR(50),
                is_suite BOOLEAN DEFAULT 0,
                is_favorite BOOLEAN DEFAULT 0,
                is_auto_detected BOOLEAN DEFAULT 0,
                notes TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                modified_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create index for favorite lookups
        conn.execute(text("""
            CREATE INDEX idx_live_installation_favorite ON live_installations(is_favorite)
        """))
        
        conn.commit()


def migration_add_musical_key_fields(engine: Engine) -> None:
    """Add musical_key, scale_type, and is_in_key fields to projects table."""
    with engine.connect() as conn:
        # Check if musical_key column already exists
        result = conn.execute(text(
            "PRAGMA table_info(projects)"
        ))
        columns = [row[1] for row in result.fetchall()]
        
        if "musical_key" not in columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN musical_key VARCHAR(10)"
            ))
        
        if "scale_type" not in columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN scale_type VARCHAR(50)"
            ))
        
        if "is_in_key" not in columns:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN is_in_key BOOLEAN"
            ))
        
        conn.commit()


# Migration registry - add new migrations here
# Each migration is a tuple of (version, description, function)
# NOTE: Must be defined AFTER the migration functions
MIGRATIONS: List[tuple] = [
    # (1, "Initial schema", None),  # Initial schema handled by create_all
    (2, "Add track_name and track_artwork_path to project_collections", migration_add_track_fields),
    (3, "Add smart collections, file_hash, and preview fields", migration_add_phase_25_fields),
    (4, "Add project metadata fields (plugins, devices, tempo, etc.)", migration_add_project_metadata_fields),
    (5, "Update FTS table to include plugins and devices for search", migration_update_fts_for_plugins),
    (6, "Add live_installations table for storing Live installations", migration_add_live_installations),
    (7, "Add arrangement_duration_seconds for calculated time duration", migration_add_arrangement_duration),
    (8, "Add musical_key, scale_type, is_in_key fields to projects", migration_add_musical_key_fields),
]


def get_schema_version(engine: Engine) -> int:
    """Get the current schema version from the database.
    
    Args:
        engine: SQLAlchemy engine.
        
    Returns:
        Current schema version number (0 if not set).
    """
    with engine.connect() as conn:
        # Check if schema_version table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ))
        if result.fetchone() is None:
            # Create schema version table
            conn.execute(text("""
                CREATE TABLE schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """))
            conn.execute(text(
                "INSERT INTO schema_version (version, description) VALUES (1, 'Initial schema')"
            ))
            conn.commit()
            return 1
        
        # Get current version
        result = conn.execute(text(
            "SELECT MAX(version) FROM schema_version"
        ))
        row = result.fetchone()
        return row[0] if row and row[0] else 1


def set_schema_version(engine: Engine, version: int, description: str) -> None:
    """Record a schema version in the database.
    
    Args:
        engine: SQLAlchemy engine.
        version: Version number to record.
        description: Description of the migration.
    """
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO schema_version (version, description) VALUES (:version, :description)"
        ), {"version": version, "description": description})
        conn.commit()


def run_migrations(engine: Engine) -> None:
    """Run any pending database migrations.
    
    Args:
        engine: SQLAlchemy engine.
    """
    current_version = get_schema_version(engine)
    
    for version, description, migration_func in MIGRATIONS:
        if version > current_version and migration_func is not None:
            print(f"Running migration {version}: {description}")
            try:
                migration_func(engine)
                set_schema_version(engine, version, description)
                print(f"Migration {version} completed successfully")
            except Exception as e:
                print(f"Migration {version} failed: {e}")
                raise


# Example migration function template:
# def migration_add_duration(engine: Engine) -> None:
#     """Add duration column to projects table."""
#     with engine.connect() as conn:
#         conn.execute(text(
#             "ALTER TABLE projects ADD COLUMN duration_seconds REAL"
#         ))
#         conn.commit()
