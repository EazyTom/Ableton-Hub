"""UI Dialogs module - Modal dialog windows."""

from .add_live_installation import AddLiveInstallationDialog
from .add_location import AddLocationDialog
from .ftue_dialog import FTUEDialog
from .create_collection import CreateCollectionDialog
from .live_version_dialog import LiveVersionDialog
from .project_details import ProjectDetailsDialog
from .select_exports_dialog import SelectExportsDialog
from .similar_projects_dialog import SimilarProjectsDialog
from .smart_collection import SmartCollectionDialog
from .song_name_generator_dialog import SongNameGeneratorDialog
from .update_dialog import UpdateDialog

__all__ = [
    "AddLocationDialog",
    "FTUEDialog",
    "CreateCollectionDialog",
    "ProjectDetailsDialog",
    "SmartCollectionDialog",
    "LiveVersionDialog",
    "AddLiveInstallationDialog",
    "SimilarProjectsDialog",
    "SelectExportsDialog",
    "SongNameGeneratorDialog",
    "UpdateDialog",
]
