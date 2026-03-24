"""Build similarity cluster trees from indexed project metadata (DB only)."""

from __future__ import annotations

import random
from collections import Counter
from datetime import datetime, UTC
from typing import Any

from . import ml_clustering as _ml_clustering
from .ml_clustering import (
    MLClusteringService,
    build_metadata_feature_matrix,
    compute_n_clusters_heuristic,
)
from .similarity_tree_models import SimilarityGroupNode, SimilarityTreeResult

_TempoLabels = MLClusteringService.TEMPO_LABELS


def _label_for_cluster(
    project_subset: list[dict[str, Any]],
) -> str:
    """Primary one-line label (tempo band + shared tools prominent)."""
    if not project_subset:
        return "Cluster"

    tempos = [
        float(p["tempo"])
        for p in project_subset
        if p.get("tempo") is not None and float(p["tempo"]) > 0
    ]
    parts: list[str] = []
    if tempos:
        avg = sum(tempos) / len(tempos)
        for (low, high), lab in _TempoLabels.items():
            if low <= avg < high:
                parts.append(lab)
                break
        else:
            parts.append(f"{avg:.0f} BPM")
    else:
        parts.append("unknown tempo")

    all_plugins: list[str] = []
    all_devices: list[str] = []
    for p in project_subset:
        all_plugins.extend(p.get("plugins") or [])
        all_devices.extend(p.get("devices") or [])
    n = len(project_subset)
    threshold = max(1.0, n / 2.0)
    if all_plugins:
        pc = Counter(all_plugins)
        common = [name for name, c in pc.most_common(3) if c >= threshold]
        if common:
            parts.append(common[0])
    elif all_devices:
        dc = Counter(all_devices)
        common = [name for name, c in dc.most_common(3) if c >= threshold]
        if common:
            parts.append(common[0])

    return " · ".join(parts) if parts else "Cluster"


def _cluster_breakdown_lines(project_subset: list[dict[str, Any]]) -> list[str]:
    """2–5 extra lines summarizing other similarity dimensions (when meaningful)."""
    if len(project_subset) < 2:
        return []

    lines: list[str] = []
    n = len(project_subset)

    keys = [
        (str(p.get("musical_key") or "").strip(), str(p.get("scale_type") or "").strip())
        for p in project_subset
    ]
    key_counts = Counter(keys)
    top_key, top_ct = key_counts.most_common(1)[0]
    if top_key[0] and top_ct >= max(2, n * 0.5):
        lines.append(f"Key: {top_key[0]} {top_key[1]}".strip())

    tracks = [float(p.get("track_count") or 0) for p in project_subset]
    if tracks:
        avg_t = sum(tracks) / len(tracks)
        lines.append(f"Avg ~{avg_t:.0f} tracks")

    with_auto = sum(1 for p in project_subset if p.get("has_automation"))
    if with_auto >= max(1, n // 2):
        lines.append(f"Automation on {100 * with_auto // n}% of projects")

    marker_counts = []
    for p in project_subset:
        m = p.get("timeline_markers")
        marker_counts.append(len(m) if isinstance(m, list) else 0)
    if marker_counts and max(marker_counts) > 0:
        avg_m = sum(marker_counts) / len(marker_counts)
        if avg_m >= 1:
            lines.append(f"Avg ~{avg_m:.1f} timeline markers")

    with_fv = sum(
        1
        for p in project_subset
        if p.get("feature_vector") and isinstance(p.get("feature_vector"), (list, tuple))
    )
    if 0 < with_fv < n:
        lines.append("Mixed ML feature vectors (some projects lack stored vectors)")
    elif with_fv == n and n > 0:
        lines.append("All projects have stored feature vectors")

    return lines[:5]


def _projects_by_ids(project_dicts: list[dict[str, Any]], ids: list[int]) -> list[dict[str, Any]]:
    by_id = {int(p["id"]): p for p in project_dicts if p.get("id") is not None}
    return [by_id[i] for i in ids if i in by_id]


def cluster_labels_to_group_nodes(
    project_dicts: list[dict[str, Any]],
    project_ids: list[int],
    labels: list[int],
) -> list[SimilarityGroupNode]:
    """Turn flat cluster labels into group nodes with project leaves."""
    clusters: dict[int, list[int]] = {}
    for pid, lab in zip(project_ids, labels):
        clusters.setdefault(int(lab), []).append(int(pid))

    root_nodes: list[SimilarityGroupNode] = []
    for ci, pids in sorted(clusters.items()):
        subset = _projects_by_ids(project_dicts, pids)
        label = _label_for_cluster(subset)
        breakdown = _cluster_breakdown_lines(subset)
        children: list[SimilarityGroupNode] = []
        for pid in pids:
            pd = next((p for p in project_dicts if int(p.get("id", -1)) == pid), None)
            name = (pd or {}).get("name", f"Project {pid}")
            children.append(
                SimilarityGroupNode(
                    kind="project",
                    node_id=f"p-{pid}",
                    label=str(name),
                    project_id=pid,
                    children=[],
                )
            )
        root_nodes.append(
            SimilarityGroupNode(
                kind="group",
                node_id=f"g-{ci}",
                label=label,
                breakdown_lines=breakdown,
                children=children,
            )
        )
    return root_nodes


def build_similarity_tree(
    project_dicts: list[dict[str, Any]],
    *,
    max_projects: int = 5000,
    random_seed: int = 42,
) -> SimilarityTreeResult:
    """Cluster projects by metadata and return a tree result for the UI.

    Does not read ``.als`` files (FR-001). Uses Ward linkage (scipy) on a weighted
    feature matrix; sklearn StandardScaler for scaling only.
    """
    warnings: list[str] = []
    params: dict[str, Any] = {
        "max_projects": max_projects,
        "pipeline": "metadata_scipy_ward",
        "engine": "scipy_ward",
    }

    if not project_dicts:
        return SimilarityTreeResult(
            warnings=["No projects in scope — add locations or adjust filters."],
            computed_at=datetime.now(UTC),
            parameters=params,
        )

    original_n = len(project_dicts)
    if original_n > max_projects:
        rng = random.Random(random_seed)
        indices = rng.sample(range(original_n), max_projects)
        indices.sort()
        project_dicts = [project_dicts[i] for i in indices]
        warnings.append(
            f"Sampled {max_projects} of {original_n} projects for clustering performance."
        )

    projects_map: dict[str, dict[str, Any]] = {}
    for p in project_dicts:
        pid = p.get("id")
        if pid is not None:
            projects_map[str(int(pid))] = {
                "display_name": p.get("name", ""),
                "tempo": p.get("tempo"),
            }

    if len(project_dicts) == 1:
        p0 = project_dicts[0]
        pid = int(p0["id"])
        leaf = SimilarityGroupNode(
            kind="project",
            node_id="p-single",
            label=str(p0.get("name", f"Project {pid}")),
            project_id=pid,
        )
        return SimilarityTreeResult(
            root_nodes=[
                SimilarityGroupNode(
                    kind="group",
                    node_id="g-single",
                    label="Single project",
                    breakdown_lines=[],
                    children=[leaf],
                )
            ],
            projects=projects_map,
            warnings=warnings
            or ["Only one project in scope — add more projects to see similarity groups."],
            computed_at=datetime.now(UTC),
            parameters=params,
        )

    if not _ml_clustering._check_sklearn():
        return SimilarityTreeResult(
            warnings=["scikit-learn is not available; install scikit-learn to use this view."]
            + warnings,
            projects=projects_map,
            computed_at=datetime.now(UTC),
            parameters=params,
        )

    try:
        from scipy.cluster.hierarchy import fcluster, linkage
    except ImportError:
        return SimilarityTreeResult(
            warnings=["scipy is not available; install scipy to use this view."] + warnings,
            projects=projects_map,
            computed_at=datetime.now(UTC),
            parameters=params,
        )

    X, project_ids, mw = build_metadata_feature_matrix(project_dicts)
    warnings.extend(mw)

    if X.shape[0] < 2 or len(project_ids) < 2:
        return SimilarityTreeResult(
            root_nodes=[],
            projects=projects_map,
            warnings=warnings or ["Not enough projects to cluster."],
            computed_at=datetime.now(UTC),
            parameters=params,
        )

    sk_mod = _ml_clustering._sklearn_modules
    assert sk_mod is not None
    StandardScaler = sk_mod["StandardScaler"]

    X_scaled = StandardScaler().fit_transform(X)
    n_clust = compute_n_clusters_heuristic(len(project_ids))
    n_clust = min(n_clust, len(project_ids))
    params["n_clusters"] = n_clust

    Z = linkage(X_scaled, method="ward")
    labels_arr = fcluster(Z, t=n_clust, criterion="maxclust")
    labels = [int(x) - 1 for x in labels_arr]

    root_nodes = cluster_labels_to_group_nodes(project_dicts, project_ids, labels)

    return SimilarityTreeResult(
        root_nodes=root_nodes,
        projects=projects_map,
        warnings=warnings,
        computed_at=datetime.now(UTC),
        parameters=params,
    )
