"""Aggregate plugin usage statistics from indexed projects."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import not_

from ..database import Project, ProjectStatus, get_session


@dataclass
class PluginUsageStat:
    """Usage summary for a single plugin."""

    name: str
    project_count: int = 0
    project_ids: list[int] = field(default_factory=list)


class PluginAnalyticsService:
    """Compute plugin frequency and project lookups from the database."""

    def get_plugin_usage_stats(self, *, limit: int | None = None) -> list[PluginUsageStat]:
        """Return plugins sorted by usage count (descending)."""
        counter: Counter[str] = Counter()
        plugin_projects: dict[str, list[int]] = {}

        with get_session() as session:
            query = session.query(Project.id, Project.plugins).filter(
                Project.status != ProjectStatus.MISSING,
                not_(Project.file_path.ilike("%/Backup/%")),
                not_(Project.file_path.ilike("%\\Backup\\%")),
            )
            for project_id, plugins_raw in query.all():
                plugins = self._normalize_plugins(plugins_raw)
                for plugin in plugins:
                    counter[plugin] += 1
                    plugin_projects.setdefault(plugin, []).append(project_id)

        stats = [
            PluginUsageStat(name=name, project_count=count, project_ids=plugin_projects[name])
            for name, count in counter.most_common(limit)
        ]
        return stats

    def get_projects_using_plugin(self, plugin_name: str) -> list[int]:
        """Return project IDs that reference the given plugin."""
        matches: list[int] = []
        needle = plugin_name.strip().lower()

        with get_session() as session:
            query = session.query(Project.id, Project.plugins).filter(
                Project.status != ProjectStatus.MISSING,
                not_(Project.file_path.ilike("%/Backup/%")),
                not_(Project.file_path.ilike("%\\Backup\\%")),
            )
            for project_id, plugins_raw in query.all():
                plugins = self._normalize_plugins(plugins_raw)
                if any(p.lower() == needle for p in plugins):
                    matches.append(project_id)
        return matches

    def get_total_projects_with_plugins(self) -> int:
        """Count active projects that have at least one plugin."""
        with get_session() as session:
            count = 0
            query = session.query(Project.plugins).filter(
                Project.status != ProjectStatus.MISSING,
            )
            for (plugins_raw,) in query.all():
                if self._normalize_plugins(plugins_raw):
                    count += 1
            return count

    @staticmethod
    def _normalize_plugins(plugins_raw) -> list[str]:
        if not plugins_raw:
            return []
        if isinstance(plugins_raw, str):
            import json

            try:
                plugins_raw = json.loads(plugins_raw)
            except json.JSONDecodeError:
                return []
        if not isinstance(plugins_raw, list):
            return []
        return [str(p).strip() for p in plugins_raw if str(p).strip()]
