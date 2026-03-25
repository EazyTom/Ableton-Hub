# Research: Similarity Cluster Tree View

## 1. Metadata-only feature matrix (no `.als` read)

**Decision**: Add a dedicated code path that builds a numeric matrix **only** from `Project` fields already in the DB (`tempo`, `plugins`, `devices`, and optionally `track_count` / `arrangement_length` for secondary structure). **Do not** call `MLFeatureExtractor` or read `.als` for the default tree (FR-001).

**Rationale**: Existing `MLClusteringService._prepare_features` prefers `feature_vector` and may parse ALS when missing—this conflicts with the spec’s default experience and constitution (predictable, read-only behavior).

**Alternatives considered**:

- Use stored `feature_vector` only — **rejected**: weights tempo vs plugins incorrectly vs spec unless retrained; also absent for many projects.
- Pairwise `SimilarityAnalyzer` distance matrix — **rejected** for large `n` (O(n²) memory/time for thousands of projects).

## 2. Tempo strongest, plugins/devices secondary

**Decision**: Encode tempo as one or more scaled numeric columns and apply **explicit higher weight** relative to plugin/device columns **before** `StandardScaler` (e.g., tempo column duplicated or multiplied by a factor &gt; 1), then cluster. Plugin/device sets encoded via **hashed multi-hot** or **global top-K vocabulary** counts to keep dimensionality bounded.

**Rationale**: Matches FR-002/FR-003 and aligns with acceptance scenario comparing same-tempo/different-plugins vs same-plugins/different-tempo.

**Alternatives considered**:

- Tune only `SimilarityAnalyzer.DEFAULT_WEIGHTS` — **insufficient** alone because clustering currently uses feature vectors, not that analyzer’s combined score per pair.
- Pure graph clustering on shared plugins — **rejected**: fails tempo-first requirement.

## 3. Hierarchical clustering and “tree branches”

**Decision**: Use **agglomerative clustering** (already imported in `ml_clustering.py`) with parameters chosen to produce a **merge tree**. Expose either `children_` from `AgglomerativeClustering(compute_full_tree=True, …)` (sklearn) or **`scipy.cluster.hierarchy.linkage`** on the same feature matrix, then convert merges to a **UI tree**: internal nodes = cluster summaries (tempo band + top shared plugins/devices), leaves = projects.

**Rationale**: Spec asks for visual tree branches; flat k-means labels are weaker for nested UX. SciPy linkage is optional if sklearn’s `children_` is sufficient for cut-to-tree.

**Alternatives considered**:

- Flat `KMeans` with artificial parent nodes — **rejected**: does not reflect hierarchical merges and is harder to justify as “tree”.
- Visual-only tree layout from flat clusters — **rejected**: misleading hierarchy.

## 4. Number of clusters / tree depth

**Decision**: Derive `n_clusters` heuristically (e.g., `min(max(2, floor(sqrt(n))), 20)`) with clamping for tiny `n`; document constants in code. Optionally run silhouette on a **subsample** for tuning — only if needed for quality; MVP can use fixed heuristic to meet SC-001 latency.

**Rationale**: Spec does not fix branch count; need deterministic defaults for tests.

## 5. Performance and large libraries

**Decision**: Run clustering in a **QThread** worker; cap or sample beyond a threshold (e.g., 5k) **with visible copy** if profiling requires (spec edge case). Prefer **scope** (P3) using existing repository filters before sampling.

**Rationale**: Constitution IV + SC-001.

## 6. UI integration

**Decision**: New widget using `QTreeWidget` or `QAbstractItemModel` + `QTreeView`; labels from `ClusterInfo`-style summaries (`suggested_label` pattern in `ml_clustering.py`). Context actions delegate to existing **open project** / **reveal** flows (FR-007).

**Rationale**: Matches existing Hub patterns and minimizes new navigation design in MVP.

## 7. Tree visualization: connectors, colors, and “real” branches

**Problem**: Users want **visible connecting branches** and/or **color-coded subtrees** so the hierarchy reads faster than a flat-looking list. The current implementation uses `QTreeWidget`, which relies on the active Qt style and stylesheet for branch lines; on dark Fusion themes those lines can be **low contrast**.

**Decision (for future work)**: Prefer **incremental** improvements before replacing the control:

1. **Style tuning** — `setIndentation`, `setAnimated`, alternating rows, and `QTreeView::branch` QSS so native expanders and connectors match `AbletonTheme` (`border`, `text_secondary`).
2. **Per-branch color** — Assign a **stable palette index** per top-level group (or per root `SimilarityGroupNode`), apply `foreground`/`background` or a **delegate-drawn left accent** on the subtree. No change to clustering output.
3. **Custom delegate** — `QStyledItemDelegate.paint` for a 2–4px colored strip + optional rounded row background; keeps keyboard accessibility and selection behavior.
4. **Optional dendrogram** — The service already computes **linkage**; `scipy.cluster.hierarchy.dendrogram` (Matplotlib) or pyqtgraph can show a **true merge diagram** in a second widget. Good for power users; different interaction model than expand/collapse.

**Python modules**:

- **PyQt6** (`QTreeView`/`QTreeWidget`, `QStyledItemDelegate`) — **primary**; best fit for app-integrated tree.
- **SciPy** — already used; supports dendrogram visualization inputs.
- **Matplotlib** (`FigureCanvasQTAgg`) — embed dendrogram if product wants scientific layout; adds dependency weight.
- **pyqtgraph** — fast plots; optional alternative to Matplotlib for dendrogram-like views.
- **NetworkX + graph layout** — generally **not** needed for a strict tree; avoid unless moving to free-form graphs.

**Alternatives considered**:

- Replace tree with **fully custom `QWidget` + `QPainter`** graph — **high effort**; reserve for if Qt tree cannot meet design.
- **Web view + D3** — **rejected** for MVP (stack, packaging, IPC).
