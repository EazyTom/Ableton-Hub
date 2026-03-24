"""Unit tests for metadata-only similarity tree clustering."""

from __future__ import annotations

import importlib.util

import pytest

from src.services.ml_clustering import (
    METADATA_FEATURE_DIM,
    build_metadata_feature_matrix,
    compute_n_clusters_heuristic,
)
from src.services.similarity_tree_service import build_similarity_tree


def test_compute_n_clusters_heuristic() -> None:
    assert compute_n_clusters_heuristic(1) == 1
    assert compute_n_clusters_heuristic(4) == 2
    assert compute_n_clusters_heuristic(100) == 10
    assert compute_n_clusters_heuristic(10_000) == 20


def test_metadata_matrix_shape_and_ids() -> None:
    projects = [
        {
            "id": 1,
            "name": "A",
            "tempo": 120.0,
            "plugins": ["Serum"],
            "devices": ["Wavetable"],
            "track_count": 8,
            "arrangement_length": 64.0,
        },
        {
            "id": 2,
            "name": "B",
            "tempo": 122.0,
            "plugins": ["Serum", "Pro-Q"],
            "devices": ["Compressor"],
            "track_count": 12,
            "arrangement_length": 128.0,
        },
    ]
    X, ids, warnings = build_metadata_feature_matrix(projects)
    assert ids == [1, 2]
    assert X.shape[0] == 2
    assert X.shape[1] == METADATA_FEATURE_DIM
    assert isinstance(warnings, list)


def test_tempo_column_weighted_stronger_than_plugin_only_signal() -> None:
    """Same plugins/devices but far tempos → larger row distance on weighted tempo cols than near tempos."""
    p_same_tools_diff_tempo = [
        {
            "id": 1,
            "name": "Lo",
            "tempo": 70.0,
            "plugins": ["X"],
            "devices": ["Y"],
            "track_count": 4,
            "arrangement_length": 16.0,
        },
        {
            "id": 2,
            "name": "Hi",
            "tempo": 170.0,
            "plugins": ["X"],
            "devices": ["Y"],
            "track_count": 4,
            "arrangement_length": 16.0,
        },
    ]
    p_diff_tools_near_tempo = [
        {
            "id": 3,
            "name": "A",
            "tempo": 120.0,
            "plugins": ["A1", "A2"],
            "devices": ["D1"],
            "track_count": 4,
            "arrangement_length": 16.0,
        },
        {
            "id": 4,
            "name": "B",
            "tempo": 121.0,
            "plugins": ["Z1", "Z2"],
            "devices": ["D9"],
            "track_count": 4,
            "arrangement_length": 16.0,
        },
    ]
    X1, _, _ = build_metadata_feature_matrix(p_same_tools_diff_tempo)
    X2, _, _ = build_metadata_feature_matrix(p_diff_tools_near_tempo)
    import numpy as np

    d1 = float(np.linalg.norm(X1[0] - X1[1]))
    d2 = float(np.linalg.norm(X2[0] - X2[1]))
    assert d1 > d2, "Far-apart tempos with identical tools should dominate raw feature distance"


def test_build_similarity_tree_empty() -> None:
    r = build_similarity_tree([])
    assert r.root_nodes == []
    assert r.warnings


def test_build_similarity_tree_single_project() -> None:
    r = build_similarity_tree(
        [
            {
                "id": 1,
                "name": "Only",
                "tempo": 90.0,
                "plugins": [],
                "devices": [],
                "track_count": 1,
                "arrangement_length": 8.0,
            }
        ]
    )
    assert len(r.root_nodes) == 1
    assert r.root_nodes[0].kind == "group"


@pytest.mark.skipif(
    importlib.util.find_spec("sklearn") is None or importlib.util.find_spec("scipy") is None,
    reason="scikit-learn or scipy not installed",
)
def test_build_similarity_tree_deterministic_small_library() -> None:
    projects = [
        {
            "id": i,
            "name": f"P{i}",
            "tempo": 100.0 + i * 5.0,
            "plugins": ["Plg"],
            "devices": ["Dev"],
            "track_count": 4,
            "arrangement_length": 32.0,
        }
        for i in range(5)
    ]
    a = build_similarity_tree(projects)
    b = build_similarity_tree(projects)
    assert len(a.root_nodes) == len(b.root_nodes)
    assert a.parameters.get("n_clusters") == b.parameters.get("n_clusters")
    assert a.parameters.get("engine") == "scipy_ward"
    assert a.parameters.get("pipeline") == "metadata_scipy_ward"
