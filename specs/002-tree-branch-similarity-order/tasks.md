---
description: "Task list: Similarity Tree — ordered branch members with scores"
---

# Tasks: Similarity Tree — ordered branch members with scores

**Input**: Design documents from `/specs/002-tree-branch-similarity-order/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md)

**Tests**: pytest tasks included (ordering, ties, anchor toy cases).

**Organization**: Phases follow user stories P1 → P2, then polish.

## Path Conventions

- Application code: `src/` (repository root `ableton_hub/`)
- Tests: `tests/unit/`

---

## Phase 1: Setup (documentation baseline)

**Purpose**: Lock design artifacts before coding.

- [x] T001 [P] Confirm `specs/002-tree-branch-similarity-order/plan.md` and `specs/002-tree-branch-similarity-order/research.md` describe medoid anchor, `SimilarityAnalyzer` parity, tie-break, and missing-score behavior; update those files if gaps appear during implementation.

---

## Phase 2: Foundational (blocking)

**Purpose**: Core ordering + data shape — **must** complete before UI wiring.

**⚠️ CRITICAL**: No user story work until this phase completes.

- [x] T002 Implement `src/services/branch_member_ordering.py`: medoid branch anchor from member project dicts, pairwise scoring via `SimilarityAnalyzer.compute_similarity`, descending sort, deterministic tie-break `(-score, name.lower(), id)` per `research.md`, and `None` scores where similarity is invalid (FR-005, FR-006).
- [x] T003 Extend `src/services/similarity_tree_models.py` and `SimilarityTreeResult.projects` (or project `SimilarityGroupNode` leaves) to carry **`similarity_to_branch_percent`** (int or `None`) for display; update `to_dict()` accordingly.
- [x] T004 Update `specs/001-ml-similarity-cluster-tree/contracts/similarity_tree_result.schema.json` to allow optional `similarity_to_branch_percent` on `projects` entries (and bump `SimilarityTreeResult.version` if required by contract rules).
- [x] T005 Integrate ordering into `src/services/similarity_tree_service.py`: after building the tree, walk group nodes, collect project leaves per group, run `branch_member_ordering` per group, **reorder** `children` so project rows are sorted, and attach percent metadata (keep clustering logic unchanged).

**Checkpoint**: Service-only tests can call ordering with toy dicts; tree structure still valid JSON.

---

## Phase 3: User Story 1 — Sorted list with % before name (Priority: P1) — MVP

**Goal**: Expanded branches show projects **most-similar-first** with **`{pct}% — {name}`** (FR-001, FR-002, FR-003).

**Independent Test**: Three+ projects under one branch; expand; descending order and leading percentage on each row.

### Implementation for User Story 1

- [x] T006 [US1] In `src/ui/workers/similarity_tree_worker.py`, after `build_similarity_tree`, load `Project` rows / dicts needed for `SimilarityAnalyzer`, invoke ordering path so `SimilarityTreeResult` includes percents and sorted children; keep heavy work on the worker thread (constitution IV).
- [x] T007 [US1] In `src/ui/widgets/similarity_tree_view.py`, render project rows using **`{percent}% — {display_name}`** when percent is present; match fallback strings for missing scores per FR-005; preserve existing tooltips/context menu where possible.

**Checkpoint**: US1 demo — tree shows ordered scored leaves.

---

## Phase 4: User Story 2 — Ties and missing metadata (Priority: P2)

**Goal**: Stable order on ties; no fake percentages (FR-005, FR-006; US2).

**Independent Test**: Same score → stable order; missing metadata → visible fallback, not arbitrary numbers.

### Implementation for User Story 2

- [x] T008 [US2] Verify `branch_member_ordering.py` and UI strings cover US2 acceptance: tie stability, `None`/invalid score display (e.g. `—` or `N/A`); add `src/ui/widgets/similarity_tree_view.py` tooltip line for breakdown when `SimilarityResult` is available (optional parity with `src/ui/widgets/recommendations_panel.py`).

---

## Phase 5: Polish & cross-cutting

**Purpose**: Tests, docs, regression.

- [x] T009 [P] Add `tests/unit/test_branch_similarity_order.py` covering medoid on a tiny synthetic set, sort order, tie-break, and anchor self 100%.
- [x] T010 Add `specs/002-tree-branch-similarity-order/quickstart.md` with manual steps: open Similarity Tree, expand branch, verify order and `%` prefix.
- [x] T011 Run `pytest` from repository root; fix regressions.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** → **Phase 2** → **Phase 3 (US1)** → **Phase 4 (US2)** → **Phase 5**
- **US2** assumes **US1** wiring exists (same modules).

### User Story Dependencies

- **US1**: Depends on Phase 2 only.
- **US2**: Depends on US1 (display + ordering paths exercised).

### Parallel Opportunities

- **T001** can run alongside environment prep (documentation only).
- **T009** [P] can run after **T002** is stable (unit tests in parallel with **T006–T007** if staffed — file conflict risk; safer after **T005**).

---

## Parallel Example (after Phase 2)

```text
Developer A: T006 similarity_tree_worker.py + T007 similarity_tree_view.py
Developer B: T009 tests/unit/test_branch_similarity_order.py (after T002 API is fixed)
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 2 (T002–T005).
2. Complete Phase 3 (T006–T007).
3. STOP and manually verify Similarity Tree ordering.

### Incremental delivery

1. Phase 2 → ordering in service layer with logging / assertions.
2. Phase 3 → user-visible `%` and order.
3. Phase 4 → edge-case polish.
4. Phase 5 → tests + quickstart + full pytest.

---

## Notes

- Do not read `.als` files on the hot path; use the same metadata fields as `SimilarityAnalyzer` elsewhere.
- For very large branches, consider batching or a progress signal in a follow-up (out of scope unless SC-001 is at risk).
