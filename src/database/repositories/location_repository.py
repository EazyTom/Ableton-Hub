"""Repository for location data access."""

import logging
from typing import Optional, List

from ..db import get_session
from ..models import Location, Project, ProjectCollection
from ...utils.logging import get_logger


class LocationRepository:
    """Repository for location queries and operations."""
    
    def __init__(self):
        """Initialize the repository."""
        self.logger = get_logger(__name__)
    
    def get_all(self, active_only: bool = True) -> List[Location]:
        """Get all locations.
        
        Args:
            active_only: If True, only return active locations.
            
        Returns:
            List of Location objects.
        """
        session = get_session()
        try:
            query = session.query(Location)
            if active_only:
                query = query.filter(Location.is_active == True)
            return query.order_by(Location.name).all()
        finally:
            session.close()
    
    def get_by_id(self, location_id: int) -> Optional[Location]:
        """Get a location by ID.
        
        Args:
            location_id: Location ID.
            
        Returns:
            Location object or None.
        """
        session = get_session()
        try:
            return session.query(Location).filter(Location.id == location_id).first()
        finally:
            session.close()
    
    def delete(self, location_id: int, delete_projects: bool = False) -> bool:
        """Delete a location.
        
        Args:
            location_id: Location ID to delete.
            delete_projects: If True, delete projects not in collections.
            
        Returns:
            True if deleted successfully.
        """
        session = get_session()
        try:
            location = session.query(Location).filter(Location.id == location_id).first()
            if not location:
                return False
            
            location_name = location.name
            
            if delete_projects:
                projects = session.query(Project).filter(Project.location_id == location_id).all()
                deleted_count = 0
                kept_count = 0
                
                for project in projects:
                    in_collection = session.query(ProjectCollection).filter(
                        ProjectCollection.project_id == project.id
                    ).first() is not None
                    
                    if in_collection:
                        project.location_id = None
                        kept_count += 1
                    else:
                        session.delete(project)
                        deleted_count += 1
                
                if deleted_count > 0:
                    self.logger.info(f"Deleted {deleted_count} project(s) not in collections")
                if kept_count > 0:
                    self.logger.info(f"Kept {kept_count} project(s) in collections (location cleared)")
            
            session.delete(location)
            session.commit()
            
            self.logger.info(f"Removed location: {location_name} (ID: {location_id})")
            return True
        finally:
            session.close()
