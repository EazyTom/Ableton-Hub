"""Data models for the Similarity Cluster Tree feature."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Literal


NodeKind = Literal["group", "project"]


@dataclass
class SimilarityGroupNode:
    """A node in the similarity tree (cluster branch or project leaf)."""

    kind: NodeKind
    node_id: str
    label: str
    children: list[SimilarityGroupNode] = field(default_factory=list)
    project_id: int | None = None
    """Set when kind == \"project\"."""

    breakdown_lines: list[str] = field(default_factory=list)
    """Extra summary lines for group nodes (tooltips / detail)."""

    similarity_to_branch_percent: int | None = None
    """When kind is project: similarity to branch medoid (0–100), or None if unavailable."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / contract interchange."""
        d: dict[str, Any] = {
            "kind": self.kind,
            "node_id": self.node_id,
            "label": self.label,
        }
        if self.project_id is not None:
            d["project_id"] = self.project_id
        if self.similarity_to_branch_percent is not None:
            d["similarity_to_branch_percent"] = self.similarity_to_branch_percent
        if self.breakdown_lines:
            d["breakdown_lines"] = list(self.breakdown_lines)
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class SimilarityTreeResult:
    """Worker → UI payload for the similarity tree view."""

    version: str = "1.2"
    root_nodes: list[SimilarityGroupNode] = field(default_factory=list)
    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Map project_id (str) → display fields."""

    warnings: list[str] = field(default_factory=list)
    computed_at: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for contract validation / logging."""
        return {
            "version": self.version,
            "root_nodes": [n.to_dict() for n in self.root_nodes],
            "projects": self.projects,
            "warnings": self.warnings,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "parameters": self.parameters,
        }
