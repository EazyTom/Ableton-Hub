---
description: "Task list for Similarity Cluster Tree View"
---

# Tasks: Similarity Cluster Tree View

**Input**: Design documents from `/specs/001-ml-similarity-cluster-tree/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: pytest tasks included per plan (metadata matrix, weighting, tree construction). UI smoke remains manual unless pytest-qt is adopted later.

**Organization**: Tasks are grouped by user story (P1 → P2 → P3) after shared infrastructure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 — only on user-story phases
- Paths are relative to the repository root `ableton_hub/` (where `src/` and `tests/` live)

## Path Conventions

- Application code: `src/`
- Tests: `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Types and contract alignment before clustering logic

- [x] T001 Create `src/services/similarity_tree_models.py` with dataclasses (or typed structures) for `SimilarityGroupNode` and `SimilarityTreeResult` matching `specs/001-ml-similarity-cluster-tree/data-model.md` and export shape compatible with `specs/001-ml-similarity-cluster-tree/contracts/similarity_tree_result.schema.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Metadata-only clustering, tree building, background worker, and unit tests — **must** complete before UI stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [x] T002 Extend `src/services/ml_clustering.py` with a **metadata-only** feature pipeline: build numeric matrix from project dicts (`tempo`, `plugins`, `devices`, optional `track_count` / `arrangement_length`) without calling `MLFeatureExtractor` or reading `.als` (FR-001)
- [x] T003 In `src/services/ml_clustering.py` (or `src/services/similarity_tree_service.py` if cleaner), apply **tempo-first weighting** before scaling/clustering (FR-002, FR-003) and run **agglomerative** clustering with parameters from `research.md` (`n_clusters` heuristic, `compute_full_tree` as needed)
- [x] T004 Implement conversion from hierarchical clustering output (e.g. sklearn `children_` or scipy linkage) to nested `SimilarityGroupNode` trees with human-readable group labels (tempo band + shared plugins/devices) in `src/services/similarity_tree_service.py`
- [x] T005 Add `src/services/similarity_tree_service.py` entrypoint `build_similarity_tree(project_dicts: list[dict[str, Any]], ...) -> SimilarityTreeResult` including edge cases: `n < 2`, missing tempo/plugins (warnings list per FR-006 / SC-004), optional **cap/sampling** with clear `warnings` when `n` exceeds threshold (research §5)
- [x] T006 Add `src/ui/workers/similarity_tree_worker.py` (`QThread`) that loads projects via `src/database/repositories/project_repository.py` (`get_all` with optional filters), maps ORM rows to dicts, calls `build_similarity_tree` off the GUI thread, and emits **signals** with `SimilarityTreeResult` or error strings (constitution IV)
- [x] T007 [P] Add `tests/unit/test_similarity_tree_clustering.py` covering metadata matrix dimensions, tempo-dominance behavior on a **fixed toy dataset**, empty/single-project outcomes, and stable tree shape for deterministic inputs

**Checkpoint**: Service + worker + tests green — user story UI can start

---

## Phase 3: User Story 1 - Open the similarity tree (Priority: P1) — MVP

**Goal**: User opens a dedicated view and sees a multi-branch tree from indexed metadata within performance expectations (SC-001)

**Independent Test**: Open the view with ≥3 projects (varied tempos, overlapping plugins); tree shows ≥2 branches; cold load feels within ~10s for ≤5k projects

### Implementation for User Story 1

- [x] T008 [US1] Create `src/ui/widgets/similarity_tree_view.py` with a `QTreeWidget` (or model/view), **loading** state, and **empty/single-project** states per spec edge cases (FR-006)
- [x] T009 [US1] Wire `SimilarityTreeWorker` to `SimilarityTreeView`: on show or explicit action, start worker; on result, populate tree on the **main thread**; handle failures with user-visible text (SC-004)
- [x] T010 [US1] Add `ViewManager.VIEW_SIMILARITY_TREE` constant in `src/ui/managers/view_manager.py`
- [x] T011 [US1] Register the new view in `src/ui/main_window.py`: add widget to content stack, `view_manager.register_view`, extend `_on_nav_click` (or equivalent) to switch to the similarity tree view
- [x] T012 [US1] Add a **sidebar** entry in `src/ui/widgets/sidebar.py` (e.g. “Similarity Tree” with an icon) that navigates to the new view

**Checkpoint**: P1 complete — user can open the view and see a similarity tree

---

## Phase 4: User Story 2 - Explore branches and members (Priority: P2)

**Goal**: Branches show understandable labels; expand/collapse lists projects under groups (FR-004, acceptance scenarios)

**Independent Test**: Expand a branch → see project names; collapse → children hidden; labels readable without raw IDs only

### Implementation for User Story 2

- [x] T013 [US2] Bind cluster/group rows to summary labels (tempo band + top shared tools) from `SimilarityTreeResult` in `src/ui/widgets/similarity_tree_view.py`
- [x] T014 [US2] Add **tooltips** or subtitle text for groups indicating **partial metadata** when warnings apply (missing tempo, etc.)
- [x] T015 [US2] When `SimilarityTreeResult.warnings` is non-empty, show a **non-blocking banner** or label at the top of the view (sampling, partial data)

**Checkpoint**: P2 complete — browsing groups matches spec

---

## Phase 5: User Story 3 - Scope and refresh (Priority: P3)

**Goal**: User can restrict which projects are clustered and refresh after library changes

**Independent Test**: Narrow scope → tree rebuilds with only scoped projects; refresh → tree matches current DB

### Implementation for User Story 3

- [x] T016 [US3] Add minimal **scope controls** on `src/ui/widgets/similarity_tree_view.py` (e.g. location filter and/or pass-through of `collection_id`, `tag_id`, `search_query`, tempo range) wired into worker’s `ProjectRepository.get_all` kwargs per `data-model.md` **TreeScope**
- [x] T017 [US3] Add **Refresh** control that cancels/restarts the worker safely and rebuilds the tree with current scope

**Checkpoint**: P3 complete — large libraries easier to manage

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: FR-007 actions, regression check, manual validation

- [x] T018 Add **context menu** on project items in `src/ui/widgets/similarity_tree_view.py` for **open in Live** / **reveal in library** by delegating to existing controllers/handlers (mirror patterns in `src/ui/widgets/recommendations_panel.py` or `src/ui/controllers/project_controller.py`) — FR-007
- [x] T019 Run `pytest` from repo root; fix any regressions introduced by this feature
- [ ] T020 Manual validation following `specs/001-ml-similarity-cluster-tree/quickstart.md` (timing perception, tempo-priority spot check, empty states) — *run locally in the app*

---

## Phase 7: Enriched matrix + scipy + labels (v2)

**Purpose**: Broader DB-backed feature matrix with explicit weighting (tempo and plugins/devices highest), scipy Ward linkage, richer group summaries and contract alignment.

- [x] T021 Add `scipy` to `requirements.txt` (numpy 2.x–compatible); keep sklearn imports lazy where still used only for scaling in the tree path.
- [x] T022 Enrich `build_metadata_feature_matrix` in `src/services/ml_clustering.py` with centralized weight constants; include optional `feature_vector`, structural, key/scale/time signature, automation, markers, Live version; update `tests/unit/test_similarity_tree_clustering.py` for matrix shape and tempo-dominance behavior.
- [x] T023 In `src/services/similarity_tree_service.py`, use `scipy.cluster.hierarchy.linkage` (Ward) + `fcluster` (`maxclust`); record `engine: scipy_ward` and `pipeline: metadata_scipy_ward` in result parameters.
- [x] T024 Expand `_project_to_dict` in `src/ui/workers/similarity_tree_worker.py` so all ORM fields required by the matrix builder are passed through.
- [x] T025 Add `breakdown_lines` on `SimilarityGroupNode`, populate from cluster summarization, set group tooltips in `src/ui/widgets/similarity_tree_view.py`, bump `SimilarityTreeResult` / contract version and `similarity_tree_result.schema.json`.
- [x] T026 Amend `specs/001-ml-similarity-cluster-tree/spec.md` (requirements, User Story 2, optional SC-005) to reflect enriched metadata weighting and multi-signal summaries.

---

## Phase 8: Richer branch visualization (plan Phase 8)

**Purpose**: Clearer hierarchy affordances—connectors, indentation, and optional per-branch color—without changing clustering semantics. See `specs/001-ml-similarity-cluster-tree/plan.md` (Phase 8) and `research.md` §7.

**Independent Test**: Open Similarity Tree with ≥3 top-level groups; branch lines/readability improve on dark theme; (if T028–T029 done) each major subtree has a distinct color cue.

- [x] T027 In `src/ui/widgets/similarity_tree_view.py`, tune the `QTreeWidget`: set sensible `setIndentation`, `setAnimated(True)`, `setAlternatingRowColors(True)`, and add **QSS** for `QTreeView` / `QTreeView::branch` (and item padding) so native expanders and connector lines read clearly against `AbletonTheme` in `src/ui/theme.py` (**Tier A**).
- [x] T028 In `src/ui/widgets/similarity_tree_view.py` `_populate_tree`, assign a **stable per–top-level-branch** color index (order- or hash-based), store branch id in `Qt.ItemDataRole.UserRole`, and apply `setForeground` / light `setBackground` across each root’s subtree (groups + projects) using a small fixed palette (**Tier B**).
- [x] T029 Add `src/ui/widgets/similarity_tree_item_delegate.py` with a `QStyledItemDelegate` that paints a **narrow left accent** (and optional row tint) using branch color from item `UserRole`; register with `setItemDelegateForColumn(0, ...)` on the tree (**Tier C**). Keep selection/focus accessible (contrast checks).
- [ ] T030 *(Optional / defer)* Refactor to `QTreeView` + `QAbstractItemModel` adapter wrapping `SimilarityGroupNode` under `src/ui/widgets/` when custom painting or extra columns need cleaner separation (**Tier D**).
- [ ] T031 *(Optional)* Add an optional **dendrogram** pane: ensure linkage is available from `src/services/similarity_tree_service.py` / `SimilarityTreeResult` (parameters or documented field), embed `scipy.cluster.hierarchy.dendrogram` via Matplotlib `FigureCanvasQTAgg` (add `matplotlib` to `requirements.txt` if not already present) (**Tier E**).
- [x] T032 Amend `specs/001-ml-similarity-cluster-tree/spec.md` (US1/US2 visual grouping cues; optional measurable SC for “distinguish branches at a glance”) to match implemented Tier A–C; cross-link `plan.md` Phase 8.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** → **Phase 2** → **Phase 3 (US1)** → **Phase 4 (US2)** → **Phase 5 (US3)** → **Phase 6** → **Phase 7** → **Phase 8**
- **US2** and **US3** assume **US1** view/worker shell exists
- **Phase 8** assumes Phase 3 view exists; **T028–T029** depend on **T027** (shared tree instance / styling baseline)

### User Story Dependencies

- **US1**: Depends on Phase 2 only
- **US2**: Depends on US1 (needs populated tree UI)
- **US3**: Depends on US1 (worker/view); can be parallelized with US2 after US1 if staffed, but sequential order above minimizes merge conflicts

### Parallel Opportunities

- **T007** can run in parallel with T004–T006 **only if** tests target stable function signatures agreed in T002–T003; safer to run T007 after T002–T005
- **T010** and **T012** [P] potential: `view_manager.py` vs `sidebar.py` — different files after `similarity_tree_view.py` exists
- **T032** can run in parallel with **T031** after visualization behavior (T027–T029) is settled
- **T030** and **T031** are optional tracks; do not block T027–T029 or T032

---

## Parallel Example: User Story 1 (after T009)

```text
# Different files after core view exists:
Task: "T010 [US1] view_manager.py constant"
Task: "T012 [US1] sidebar.py nav item"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. STOP and validate: open view, see tree, performance sanity check
4. Then US2 → US3 → Polish

### Incremental Delivery

1. Phase 2 + US1 → demo MVP
2. Add US2 (labels/banners)
3. Add US3 (scope/refresh)
4. Polish + FR-007 menu
5. Phase 8 (T027+) for branch styling/colors; optional T030–T031 afterward

---

## Notes

- Mark each task `[x]` in this file as work completes (`/speckit.implement` may do this automatically)
- Keep clustering **off** the GUI thread; never block `QApplication` main thread during matrix build or `fit` (constitution IV)
