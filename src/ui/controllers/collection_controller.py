"""Controller for managing collections."""

import logging
from typing import Optional, List

from PyQt6.QtCore import QObject, pyqtSignal

from ...database import get_session, Collection
from ...utils.logging import get_logger


class CollectionController(QObject):
    """Manages collection operations."""
    
    # Signals
    collection_created = pyqtSignal(int)  # collection_id
    collection_updated = pyqtSignal(int)  # collection_id
    collection_deleted = pyqtSignal(int)  # collection_id
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the collection controller.
        
        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
    
    def get_collection(self, collection_id: int) -> Optional[Collection]:
        """Get a collection by ID.
        
        Args:
            collection_id: Collection ID.
            
        Returns:
            Collection object or None if not found or on error.
        """
        try:
            with get_session() as session:
                return session.query(Collection).filter(Collection.id == collection_id).first()
        except Exception as e:
            self.logger.error(f"Error getting collection {collection_id}: {e}", exc_info=True)
            return None
    
    def get_all_collections(self) -> List[Collection]:
        """Get all collections.
        
        Returns:
            List of Collection objects.
        """
        with get_session() as session:
            return session.query(Collection).order_by(Collection.name).all()
    
    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection.
        
        Args:
            collection_id: Collection ID to delete.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        try:
            with get_session() as session:
                collection = session.query(Collection).filter(Collection.id == collection_id).first()
                if collection:
                    session.delete(collection)
                    session.commit()
                    self.logger.info(f"Deleted collection: {collection.name} (ID: {collection_id})")
                    self.collection_deleted.emit(collection_id)
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Error deleting collection {collection_id}: {e}", exc_info=True)
            return False
