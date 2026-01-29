"""Database engine and session management for Ableton Hub."""

import logging
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.engine import Engine

from ..utils.paths import get_database_path
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine: Optional[Engine] = None
_session_factory: Optional[scoped_session] = None


def get_engine(db_path: Optional[Path] = None) -> Engine:
    """Get or create the SQLAlchemy engine.
    
    Args:
        db_path: Optional custom database path.
        
    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine
    
    if _engine is None:
        path = db_path or get_database_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine with SQLite optimizations
        _engine = create_engine(
            f"sqlite:///{path}",
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            connect_args={
                "check_same_thread": False,  # Allow multi-threaded access
                "timeout": 30,
            }
        )
        
        # Enable SQLite optimizations
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            # Use WAL mode for better concurrent access
            cursor.execute("PRAGMA journal_mode=WAL")
            # Optimize for speed
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
    
    return _engine


def get_session_factory() -> scoped_session:
    """Get or create the session factory.
    
    Returns:
        Scoped session factory for thread-safe sessions.
    """
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        _session_factory = scoped_session(factory)
    
    return _session_factory


def get_session() -> Session:
    """Get a database session.
    
    Returns:
        SQLAlchemy Session instance.
    """
    return get_session_factory()()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.
    
    Usage:
        with session_scope() as session:
            session.add(obj)
            # Auto-commits on success, rolls back on exception
    
    Yields:
        Database session.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(db_path: Optional[Path] = None) -> None:
    """Initialize the database, creating tables if needed.
    
    Args:
        db_path: Optional custom database path.
    """
    from .models import Base
    from .migrations import run_migrations
    
    engine = get_engine(db_path)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Run any pending migrations
    run_migrations(engine)
    
    # Create FTS5 virtual table for full-text search
    _create_fts_table(engine)


def _create_fts_table(engine: Engine) -> None:
    """Create the FTS5 virtual table for project search.
    
    Args:
        engine: SQLAlchemy engine.
    """
    with engine.connect() as conn:
        # Check if FTS table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects_fts'"
        ))
        if result.fetchone() is None:
            # Create FTS5 virtual table with plugins and devices
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
            
            # Create triggers to keep FTS in sync
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
            
            conn.commit()


def search_projects_fts(query: str, limit: int = 100) -> list:
    """Search projects using full-text search.
    
    Args:
        query: Search query string.
        limit: Maximum results to return.
        
    Returns:
        List of project IDs matching the query.
    """
    with get_engine().connect() as conn:
        # Escape special FTS characters
        safe_query = query.replace('"', '""')
        
        result = conn.execute(text(f"""
            SELECT rowid FROM projects_fts
            WHERE projects_fts MATCH '"{safe_query}"*'
            ORDER BY rank
            LIMIT :limit
        """), {"limit": limit})
        
        return [row[0] for row in result.fetchall()]


def close_database() -> None:
    """Close database connections and cleanup."""
    global _engine, _session_factory
    
    if _session_factory is not None:
        _session_factory.remove()
        _session_factory = None
    
    if _engine is not None:
        _engine.dispose()
        _engine = None


def reset_database() -> bool:
    """Reset the database by deleting it and reinitializing.
    
    This function safely closes all connections, deletes the database file,
    and reinitializes a fresh database. Use with caution!
    
    Returns:
        True if reset was successful, False otherwise.
    """
    global _engine, _session_factory
    
    try:
        # Close all existing connections
        if _session_factory is not None:
            _session_factory.remove()
            _session_factory = None
        
        if _engine is not None:
            _engine.dispose()
            _engine = None
        
        # Get database path
        db_path = get_database_path()
        
        # Delete database file and related files (WAL, SHM)
        if db_path.exists():
            db_path.unlink()
            logger.info(f"Deleted database file: {db_path}")
        
        # Delete WAL and SHM files if they exist
        wal_path = db_path.with_suffix('.db-wal')
        shm_path = db_path.with_suffix('.db-shm')
        if wal_path.exists():
            wal_path.unlink()
            logger.info(f"Deleted WAL file: {wal_path}")
        if shm_path.exists():
            shm_path.unlink()
            logger.info(f"Deleted SHM file: {shm_path}")
        
        # Reinitialize database
        init_database()
        logger.info("Database reset complete - fresh database initialized")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset database: {e}", exc_info=True)
        # Try to reinitialize even if deletion failed
        try:
            init_database()
        except Exception as init_error:
            logger.error(f"Failed to reinitialize database: {init_error}", exc_info=True)
        return False
