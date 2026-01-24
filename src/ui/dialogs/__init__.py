"""UI Dialogs module - Modal dialog windows."""

from .add_location import AddLocationDialog
from .create_collection import CreateCollectionDialog
from .project_details import ProjectDetailsDialog
from .smart_collection import SmartCollectionDialog
from .live_version_dialog import LiveVersionDialog
from .add_live_installation import AddLiveInstallationDialog
from .similar_projects_dialog import SimilarProjectsDialog

__all__ = [
    "AddLocationDialog",
    "CreateCollectionDialog",
    "ProjectDetailsDialog",
    "SmartCollectionDialog",
    "LiveVersionDialog",
    "AddLiveInstallationDialog",
    "SimilarProjectsDialog",
]
