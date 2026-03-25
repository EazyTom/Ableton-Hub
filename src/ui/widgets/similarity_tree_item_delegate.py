"""Item delegate for Similarity Tree: left accent stripe per top-level branch group."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QTreeWidget, QWidget


class SimilarityTreeItemDelegate(QStyledItemDelegate):
    """Paints a narrow colored strip on the left of each row when `branch_index` is in UserRole."""

    ACCENT_WIDTH_PX = 4

    def __init__(self, tree: QTreeWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tree = tree

    _PALETTE_KEYS = (
        "accent",
        "info",
        "success",
        "warning",
        "cloud",
        "network",
        "local",
        "border_focus",
    )

    @classmethod
    def branch_color(cls, branch_index: int) -> QColor:
        """Stable color for a branch index (theme-aware via AbletonTheme)."""
        from ..theme import AbletonTheme

        key = cls._PALETTE_KEYS[branch_index % len(cls._PALETTE_KEYS)]
        return AbletonTheme.get_qcolor(key)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().paint(painter, option, index)

        item = self._tree.itemFromIndex(index)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        bi = data.get("branch_index")
        if bi is None:
            return
        color = self.branch_color(int(bi))

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        r = option.rect
        painter.fillRect(r.left(), r.top(), self.ACCENT_WIDTH_PX, r.height(), color)
        painter.restore()
