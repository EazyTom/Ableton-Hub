"""Repository for collection data access."""

import logging
from typing import Optional, List

from ..db import get_session
from ..models import Collection
from ...utils.logging import get_logger


class CollectionRepository:
    """Repository for collection queries and operations."""
    
    def __init__(self):
        """Initialize the repository."""
        self.logger = get_logger(__name__)
    
    def get_all(self) -> List[Collection]:
        """Get all collections.
        
        Returns:
            List of Collection objects.
        """
        session = get_session()
        try:
            return session.query(Collection).order_by(Collection.name).all()
        finally:
            session.close()
    
    def get_by_id(self, collection_id: int) -> Optional[Collection]:
        """Get a collection by ID.
        
        Args:
            collection_id: Collection ID.
            
        Returns:
            Collection object or None.
        """
        session = get_session()
        try:
            return session.query(Collection).filter(Collection.id == collection_id).first()
        finally:
            session.close()
    
    def delete(self, collection_id: int) -> bool:
        """Delete a collection.
        
        Args:
            collection_id: Collection ID to delete.
            
        Returns:
            True if deleted successfully.
        """
        session = get_session()
        try:
            collection = session.query(Collection).filter(Collection.id == collection_id).first()
            if collection:
                session.delete(collection)
                session.commit()
                self.logger.info(f"Deleted collection: {collection.name} (ID: {collection_id})")
                return True
            return False
        finally:
            session.close()
