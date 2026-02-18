"""Services module - Business logic for scanning, watching, and network discovery.

This module includes core services for project management as well as
ML/AI services for advanced analysis (Phase 5+):
- Feature extraction for ML pipelines
- Project similarity detection
- Clustering and grouping
- Recommendation engine

ML/AI services are lazy-loaded to avoid slow startup from heavy library imports
(numpy, sklearn, librosa). They are only imported when actually accessed.
"""

# Core services - loaded eagerly (lightweight, needed at startup)
from .als_parser import ALSParser, ClipInfo, DeviceChainInfo, ExtendedMetadata, ProjectMetadata
from .audio_preview import AudioPreviewGenerator
from .duplicate_detector import DuplicateDetector
from .export_tracker import ExportTracker
from .health_calculator import HealthCalculator
from .link_scanner import LinkScanner
from .live_detector import LiveDetector, LiveVersion
from .live_launcher import LiveLauncher
from .marker_extractor import MarkerExtractor
from .remote_sync import RemoteSync
from .scanner import ProjectScanner
from .smart_collections import SmartCollectionService
from .update_checker import UpdateChecker
from .watcher import FileWatcher

# ML/AI Services - lazy-loaded to avoid slow startup
# These import heavy libraries (numpy, sklearn, librosa) so we defer them

# Lazy-loading registry
_ML_SERVICES = {
    # asd_parser
    "ASDParser": ("asd_parser", "ASDParser"),
    "ClipAnalysisData": ("asd_parser", "ClipAnalysisData"),
    "WarpMarker": ("asd_parser", "WarpMarker"),
    "find_asd_files": ("asd_parser", "find_asd_files"),
    # ml_feature_extractor
    "MLFeatureExtractor": ("ml_feature_extractor", "MLFeatureExtractor"),
    "ProjectFeatureVector": ("ml_feature_extractor", "ProjectFeatureVector"),
    "AudioFeatures": ("ml_feature_extractor", "AudioFeatures"),
    # similarity_analyzer
    "SimilarityAnalyzer": ("similarity_analyzer", "SimilarityAnalyzer"),
    "SimilarityResult": ("similarity_analyzer", "SimilarityResult"),
    "SimilarProject": ("similarity_analyzer", "SimilarProject"),
    # ml_clustering
    "MLClusteringService": ("ml_clustering", "MLClusteringService"),
    "ClusterInfo": ("ml_clustering", "ClusterInfo"),
    "ClusteringResult": ("ml_clustering", "ClusteringResult"),
    # recommendation_engine
    "RecommendationEngine": ("recommendation_engine", "RecommendationEngine"),
    "Recommendation": ("recommendation_engine", "Recommendation"),
    "RecommendationSet": ("recommendation_engine", "RecommendationSet"),
}

# Cache for lazy-loaded modules
_loaded_modules = {}


def __getattr__(name: str):
    """Lazy-load ML/AI services on first access.

    This avoids importing heavy libraries (numpy, sklearn, librosa) at startup.
    """
    if name in _ML_SERVICES:
        module_name, attr_name = _ML_SERVICES[name]

        # Check if module is already loaded
        if module_name not in _loaded_modules:
            import importlib

            _loaded_modules[module_name] = importlib.import_module(f".{module_name}", __package__)

        return getattr(_loaded_modules[module_name], attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core services (eager)
    "ProjectScanner",
    "FileWatcher",
    "ExportTracker",
    "LinkScanner",
    "RemoteSync",
    "SmartCollectionService",
    "DuplicateDetector",
    "HealthCalculator",
    "AudioPreviewGenerator",
    "MarkerExtractor",
    "ALSParser",
    "ProjectMetadata",
    "ExtendedMetadata",
    "DeviceChainInfo",
    "ClipInfo",
    "LiveDetector",
    "LiveVersion",
    "LiveLauncher",
    "UpdateChecker",
    # ML/AI services (lazy-loaded)
    "ASDParser",
    "ClipAnalysisData",
    "WarpMarker",
    "find_asd_files",
    "MLFeatureExtractor",
    "ProjectFeatureVector",
    "AudioFeatures",
    "SimilarityAnalyzer",
    "SimilarityResult",
    "SimilarProject",
    "MLClusteringService",
    "ClusterInfo",
    "ClusteringResult",
    "RecommendationEngine",
    "Recommendation",
    "RecommendationSet",
]
