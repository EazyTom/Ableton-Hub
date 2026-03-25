"""Order similarity-tree branch members by pairwise similarity to a medoid anchor (Same as Similarities)."""

from __future__ import annotations

from typing import Any

from .similarity_analyzer import SimilarityAnalyzer, SimilarityResult
from .similarity_tree_models import SimilarityGroupNode, SimilarityTreeResult


def compute_medoid_anchor_id(
    member_ids: list[int],
    by_id: dict[int, dict[str, Any]],
    analyzer: SimilarityAnalyzer,
) -> int:
    """Pick member minimizing sum of (1 - similarity) to others; tie-break smallest id."""
    if not member_ids:
        raise ValueError("member_ids must not be empty")
    if len(member_ids) == 1:
        return member_ids[0]

    best_id: int | None = None
    best_sum = float("inf")
    for i in sorted(member_ids):
        di = by_id.get(i)
        if di is None:
            continue
        total = 0.0
        for j in member_ids:
            if i == j:
                continue
            dj = by_id.get(j)
            if dj is None:
                total += 1.0
                continue
            sim = analyzer.compute_similarity(di, dj).overall_similarity
            total += 1.0 - float(sim)
        if best_id is None or total < best_sum or (total == best_sum and i < best_id):
            best_sum = total
            best_id = i
    return best_id if best_id is not None else member_ids[0]


def _percent_from_result(res: SimilarityResult | None) -> int | None:
    if res is None:
        return None
    pct = int(round(res.overall_similarity * 100))
    return max(0, min(100, pct))


def sort_members_by_anchor_similarity(
    anchor_id: int,
    member_ids: list[int],
    by_id: dict[int, dict[str, Any]],
    analyzer: SimilarityAnalyzer,
) -> list[tuple[int, int | None, SimilarityResult | None]]:
    """Return (project_id, percent or None, SimilarityResult or None) sorted for display."""
    anchor = by_id.get(anchor_id)
    rows: list[tuple[int, int | None, SimilarityResult | None]] = []

    for pid in member_ids:
        cand = by_id.get(pid)
        if cand is None:
            rows.append((pid, None, None))
            continue
        if anchor is None:
            rows.append((pid, None, None))
            continue
        res = analyzer.compute_similarity(anchor, cand)
        pct = _percent_from_result(res)
        if pid == anchor_id:
            pct = 100
        rows.append((pid, pct, res))

    def sort_key(
        item: tuple[int, int | None, SimilarityResult | None],
    ) -> tuple[float, str, int]:
        pid, _pct, res = item
        name = str(by_id.get(pid, {}).get("name", "")).lower()
        if res is not None:
            ov = float(res.overall_similarity)
        else:
            ov = -1.0
        return (-ov, name, pid)

    rows.sort(key=sort_key)
    return rows


def _reorder_and_annotate_projects(
    group: SimilarityGroupNode,
    by_id: dict[int, dict[str, Any]],
    analyzer: SimilarityAnalyzer,
    projects_map: dict[str, dict[str, Any]],
) -> None:
    """Sort direct project leaves; recurse into child groups."""
    group_children = [c for c in group.children if c.kind == "group"]
    project_nodes = [c for c in group.children if c.kind == "project"]

    for g in group_children:
        _reorder_and_annotate_projects(g, by_id, analyzer, projects_map)

    if not project_nodes:
        group.children = group_children + project_nodes
        return

    member_ids = [int(n.project_id) for n in project_nodes if n.project_id is not None]
    if not member_ids:
        group.children = group_children + project_nodes
        return

    anchor_id = compute_medoid_anchor_id(member_ids, by_id, analyzer)
    ordered = sort_members_by_anchor_similarity(anchor_id, member_ids, by_id, analyzer)

    by_pid = {n.project_id: n for n in project_nodes if n.project_id is not None}
    new_project_nodes: list[SimilarityGroupNode] = []
    for pid, pct, res in ordered:
        node = by_pid.get(pid)
        if node is None:
            continue
        node.similarity_to_branch_percent = pct
        sid = str(pid)
        if sid in projects_map:
            projects_map[sid]["similarity_to_branch_percent"] = pct
            if res is not None:
                projects_map[sid]["similarity_tooltip"] = analyzer.get_similarity_explanation(res)
        new_project_nodes.append(node)

    group.children = group_children + new_project_nodes


def apply_branch_similarity_ordering(
    result: SimilarityTreeResult,
    project_dicts: list[dict[str, Any]],
    analyzer: SimilarityAnalyzer | None = None,
) -> None:
    """Mutate tree and projects map: sort project leaves per group; set similarity percents."""
    own = analyzer or SimilarityAnalyzer()
    by_id = {int(p["id"]): p for p in project_dicts if p.get("id") is not None}

    for root in result.root_nodes:
        if root.kind == "group":
            _reorder_and_annotate_projects(root, by_id, own, result.projects)
