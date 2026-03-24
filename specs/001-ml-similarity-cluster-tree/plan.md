# Implementation Plan: Similarity Cluster Tree View

**Branch**: `001-ml-similarity-cluster-tree` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-ml-similarity-cluster-tree/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver a **Similarity Cluster Tree** view that groups indexed Ableton projects into expandable branches using **only database-backed metadata** (tempo, plugins, devices, and related fields already on `Project`). **Tempo** must dominate **plugin/device overlap** in the grouping (FR-002/003). Use **agglomerative (hierarchical) clustering** so the UI can render a **merge tree** (nested branches) without re-parsing `.als` files for the default path. Heavy computation runs on a **background worker**; the Qt UI stays responsive (constitution IV). **pytest** covers the metadata feature builder, weighting behavior, and tree construction from a fixed toy dataset.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyQt6, SQLAlchemy, numpy, scikit-learn (existing `requirements.txt`); optional scipy for linkage/dendrogram helpers if needed for tree extraction  
**Storage**: SQLite via SQLAlchemy (`Project` rows: `tempo`, `plugins`, `devices`, `track_count`, etc.)  
**Testing**: pytest for services; manual or pytest-qt later for UI smoke if already adopted  
**Target Platform**: Windows 10/11 desktop (primary); same codebase runs cross-platform where PyQt6 is supported  
**Project Type**: desktop-app (Ableton Hub)  
**Performance Goals**: Render first tree within **10 seconds** for up to **5,000** projects in scope (per SC-001); clustering must not block the GUI thread  
**Constraints**: No modification of user `.als` files (FR-005); metadata-only default path (FR-001)—do **not** call `MLFeatureExtractor` / ALS parse for the default tree build  
**Scale/Scope**: Typical libraries &lt; 5k projects in view; optional **scope** (P3) reuses `ProjectRepository.get_all` filters; optional **sampling** or **cap** with user-visible message if profiling shows &gt;5k in one shot is too slow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify against `.specify/memory/constitution.md` (Ableton Hub):

- **User project safety**: Read-only grouping from DB; no writes to `.als` or user media. **PASS** (FR-001, FR-005; implementation avoids ALS reads on default path).
- **Stack conformance**: Python 3.11+, PyQt6, SQLAlchemy, type hints on new public APIs. **PASS**.
- **Regression tests**: pytest for clustering-on-metadata and tree-shape logic (not UI-only). **PASS** (planned under `tests/`).
- **UI threading**: Clustering + matrix build in `QThread` worker; signals deliver results to main thread for model updates. **PASS** (mirrors `project_properties_view` / `AudioScanWorker` patterns).
- **Focused scope**: Changes limited to new view, service extensions, repository usage, tests. **PASS**.

**Post-design re-check**: Same — no violations; Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-ml-similarity-cluster-tree/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
└── tasks.md             # /speckit.tasks (not created here)
```

### Source Code (repository root)

```text
ableton_hub/src/
├── services/
│   ├── ml_clustering.py           # Extend: metadata-only feature prep + hierarchical tree export
│   └── similarity_analyzer.py     # Reuse tempo/Jaccard helpers where appropriate
├── database/
│   └── repositories/project_repository.py   # Reuse get_all / filters for scope (P3)
├── ui/
│   ├── widgets/                   # New: similarity_tree_view.py (QTreeWidget or model/view)
│   └── workers/                   # New: similarity_tree_worker.py (QThread)
└── ...

ableton_hub/tests/
├── unit/
│   └── test_similarity_tree_clustering.py   # Metadata matrix, weights, small tree
└── ...
```

**Structure Decision**: Single desktop app under `ableton_hub/src/`; feature adds **service** logic for metadata-weighted clustering and tree building, a **worker** for background execution, and a **widget** (or dialog) for the tree UI. No new top-level package.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

None.

## Phase 0 & Phase 1 Outputs

- **research.md**: Decisions on metadata feature construction, tempo weighting vs plugin/device, hierarchical tree extraction, and large-`n` mitigation.
- **data-model.md**: Logical entities for tree nodes, cluster summaries, and scope.
- **contracts/similarity_tree_result.schema.json**: JSON shape from worker → UI (optional interchange for tests).
- **quickstart.md**: Manual validation steps for developers.

Agent context updated via `.specify/scripts/powershell/update-agent-context.ps1 -AgentType cursor-agent`.
