# Implementation Plan: Similarity Tree — ordered branch members with scores

**Branch**: `002-tree-branch-similarity-order` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)

## Summary

Order **project leaves** under each **similarity group (branch)** by **descending similarity to a single branch anchor**, and show **`{percent}%` before the project name**, using the **same pairwise similarity pipeline** as the existing Similarities flows (`SimilarityAnalyzer.compute_similarity` / the same inputs used by `find_similar_projects`). The branch anchor is **one logical reference** derived from the members (see **research.md**): default recommendation is a **medoid** project (member minimizing average distance to others) so the anchor is always a real `Project` row and scores stay comparable to picking that project in Similarities.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyQt6, SQLAlchemy, existing `SimilarityAnalyzer` in `src/services/similarity_analyzer.py`  
**Storage**: SQLite via SQLAlchemy — reuse `Project` / repository patterns; no `.als` reads required for scoring if indexed metadata exists  
**Testing**: `pytest` unit tests for sort stability, tie-break, and score parity on a toy dict set  
**Target Platform**: Windows 10/11 desktop (primary)  
**Constraints**: No modification of user project files (FR-004); heavy scoring stays off the GUI thread (worker), matching Similarity Tree patterns  

## Constitution Check

- **User project safety**: Read-only DB metadata for similarity. **PASS**.  
- **Stack conformance**: Python + type hints, PyQt6. **PASS**.  
- **Regression tests**: Unit tests for ordering. **PASS** (planned).  
- **UI threading**: Batch work in `SimilarityTreeWorker` or sub-call after clustering; avoid blocking main thread for large branches. **PASS**.  

## Project Structure

### Documentation (this feature)

```text
specs/002-tree-branch-similarity-order/
├── plan.md          # This file
├── spec.md
├── research.md      # Anchor selection + parity notes (add during Phase 2)
├── tasks.md         # /speckit.tasks
└── checklists/
```

### Source (repository root `ableton_hub/`)

```text
src/services/similarity_analyzer.py     # Reuse compute_similarity / SimilarProject patterns
src/services/similarity_tree_service.py # Post-process groups: order + attach scores
src/services/similarity_tree_models.py  # Optional fields on nodes or projects map
src/ui/workers/similarity_tree_worker.py
src/ui/widgets/similarity_tree_view.py
tests/unit/test_branch_similarity_order.py  # New
specs/001-ml-similarity-cluster-tree/contracts/similarity_tree_result.schema.json  # Optional bump
```

## Complexity Tracking

None.

## Phase 0 / Research Output

- Add **research.md**: document **medoid** (or agreed alternative) as branch anchor; document tie-break (`(-score, name, id)`); document display format aligned with `RecommendationsPanel` / project details (`%` before name per user request).
