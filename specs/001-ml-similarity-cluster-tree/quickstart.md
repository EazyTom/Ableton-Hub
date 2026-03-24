# Quickstart: Similarity Cluster Tree View (manual validation)

## Prerequisites

- Dev environment per `README.md` / `.cursorrules` (`venv`, Python 3.11+).
- Library with at least **three** indexed projects with **varied tempos** and some **overlapping plugins**.

## Steps

1. Launch the app (`python -m src.main` from `ableton_hub/`).
2. Open the **Similarity Cluster Tree** entry point (exact location implemented with the feature—menu, sidebar, or tools).
3. **P1**: Confirm a **tree** appears with **multiple branches** when data supports it; wait time should feel within **~10 seconds** for libraries up to a few thousand projects.
4. **P2**: Expand a branch; confirm **project names** list. Collapse; confirm children hide.
5. **Tempo priority (spot check)**: Identify two pairs—(A) close tempo, different plugins; (B) identical plugins, very different tempo. Confirm (A) tends to co-locate more than (B) (per spec acceptance).
6. **FR-005 / FR-001**: Confirm opening the view does **not** modify `.als` files on disk (e.g., observe file timestamps unchanged during view-only use).
7. **Failure / empty**: Test with **zero** or **one** project in scope; confirm **empty state** or explanation, not a crash.

## Automated tests (developers)

```powershell
cd D:\Repos\Ableton-Hub\ableton_hub
pytest tests\unit\test_similarity_tree_clustering.py -v
```

(Add or adjust path once tests land.)
