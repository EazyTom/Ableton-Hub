# Quickstart: Branch similarity ordering

**Feature**: `002-tree-branch-similarity-order`

## Manual check

1. Open Ableton Hub and navigate to **Similarity Tree** (sidebar).
2. Ensure a scope with **at least three projects** in one cluster (expand a branch).
3. Expand a **group** branch.
4. Confirm each **project** row shows **`{percent}% — {display name}`** with the **highest** similarity at the **top** (most similar to the branch first).
5. Hover a project row: tooltip should include **Similarity to branch: {pct}%** and a short **explanation** when available.
6. If a project cannot be scored, the row should show **`— —`** before the name instead of a fake percentage.

## Automated regression

From repo root (`ableton_hub/`):

```powershell
pytest tests\unit\test_branch_similarity_order.py tests\unit\test_similarity_tree_clustering.py -v
```
