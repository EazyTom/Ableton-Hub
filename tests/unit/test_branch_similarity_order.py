"""Unit tests for medoid anchor and branch member ordering."""

from __future__ import annotations

from src.services.branch_member_ordering import (
    apply_branch_similarity_ordering,
    compute_medoid_anchor_id,
    sort_members_by_anchor_similarity,
)
from src.services.similarity_analyzer import SimilarityAnalyzer
from src.services.similarity_tree_models import SimilarityGroupNode, SimilarityTreeResult


def _dict(pid: int, name: str, tempo: float, plugins: list[str]) -> dict:
    return {
        "id": pid,
        "name": name,
        "tempo": tempo,
        "plugins": plugins,
        "devices": [],
        "track_count": 4,
        "arrangement_length": 16.0,
        "audio_tracks": 2,
        "midi_tracks": 2,
        "return_tracks": 0,
        "feature_vector": None,
        "musical_key": "",
        "scale_type": "",
        "time_signature": "",
        "has_automation": False,
        "timeline_markers": [],
        "ableton_version": "",
    }


def test_medoid_single_member() -> None:
    analyzer = SimilarityAnalyzer()
    by_id = {1: _dict(1, "A", 120.0, ["Serum"])}
    assert compute_medoid_anchor_id([1], by_id, analyzer) == 1


def test_sort_anchor_self_is_100_percent() -> None:
    analyzer = SimilarityAnalyzer()
    by_id = {
        1: _dict(1, "A", 120.0, ["Serum"]),
        2: _dict(2, "B", 120.0, ["Serum"]),
    }
    ordered = sort_members_by_anchor_similarity(1, [1, 2], by_id, analyzer)
    by_pid = {pid: (pct, res) for pid, pct, res in ordered}
    assert by_pid[1][0] == 100
    assert by_pid[2][0] is not None


def test_tie_break_stable_by_name() -> None:
    analyzer = SimilarityAnalyzer()
    # Anchor has an extra plugin so self-similarity wins; remaining two tie → name order
    by_id = {
        1: _dict(1, "Zed", 120.0, ["Serum", "Extra"]),
        2: _dict(2, "Amy", 120.0, ["Serum"]),
        3: _dict(3, "Bob", 120.0, ["Serum"]),
    }
    ordered = sort_members_by_anchor_similarity(1, [1, 2, 3], by_id, analyzer)
    ids = [pid for pid, _, _ in ordered]
    assert ids[0] == 1
    rest = ids[1:]
    assert rest == sorted(rest, key=lambda i: (str(by_id[i]["name"]).lower(), i))


def test_apply_sets_percent_on_result() -> None:
    analyzer = SimilarityAnalyzer()
    leaf1 = SimilarityGroupNode(
        kind="project",
        node_id="p-1",
        label="A",
        project_id=1,
    )
    leaf2 = SimilarityGroupNode(
        kind="project",
        node_id="p-2",
        label="B",
        project_id=2,
    )
    root = SimilarityGroupNode(
        kind="group",
        node_id="g-0",
        label="G",
        children=[leaf1, leaf2],
    )
    d1 = _dict(1, "A", 120.0, ["Serum"])
    d2 = _dict(2, "B", 121.0, ["Serum"])
    result = SimilarityTreeResult(
        root_nodes=[root],
        projects={
            "1": {"display_name": "A", "tempo": 120.0},
            "2": {"display_name": "B", "tempo": 121.0},
        },
    )
    apply_branch_similarity_ordering(result, [d1, d2], analyzer=analyzer)
    assert leaf1.similarity_to_branch_percent is not None
    assert leaf2.similarity_to_branch_percent is not None
    assert "similarity_to_branch_percent" in result.projects["1"]
