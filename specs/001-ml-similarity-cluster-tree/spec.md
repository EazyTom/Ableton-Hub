# Feature Specification: Similarity Cluster Tree View

**Feature Branch**: `001-ml-similarity-cluster-tree`  
**Created**: 2026-03-22  
**Status**: Draft  
**Input**: User description: "new feature to use ML clustering to show visual tree branches of projects with similarity across common devices and plugins used, and similarity across tempos being the strongest similarities using what project metadata is available in the db"

## Assumptions

- Indexed project metadata (including tempo, plugins, devices, and other fields stored in the database such as structural counts, optional ML feature vectors, key/time signature, automation, markers, and Live version) is already present from existing library scans; this feature does not require re-reading project files for basic operation.
- Clustering uses this broad set of indexed metadata, while **tempo proximity and plugin/device overlap remain the strongest weighted factors** (FR-002, FR-003).
- “Strongest” similarity means tempo proximity outweighs plugin/device overlap when the model must rank or split groups, ahead of other metadata dimensions (see functional requirements).
- The primary surface is a dedicated view or panel in the desktop app where the tree lives; exact entry point (menu vs. sidebar) is a product detail left to design during planning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open the similarity tree (Priority: P1)

A producer opens a view that shows their projects organized as a branching tree. Each branch represents a group of projects that are more like each other than like projects in other branches, using only information already stored about each project. Tempo closeness is treated as the strongest signal; overlap of plugins and devices is the next most important. The producer can see the structure at a glance without running a separate similarity search for each project.

**Why this priority**: Without the tree, the feature delivers no value; this is the core outcome.

**Independent Test**: Open the view with a library that has varied tempos and overlapping plugins; confirm a tree appears with multiple branches and child projects.

**Acceptance Scenarios**:

1. **Given** at least three indexed projects with different tempos and some shared plugins, **When** the user opens the similarity tree view, **Then** the system shows a tree with at least two branches and projects appear under branches.
2. **Given** two projects with nearly the same tempo but different plugins, **When** the tree is generated, **Then** those projects are more likely to appear in the same branch than two projects with identical plugins but very different tempos (tempo priority).

---

### User Story 2 - Explore branches and members (Priority: P2)

The producer expands and collapses branches to see which projects sit in each group. Each group is understandable from labels or short summaries: **tempo band and shared tools remain prominent**, and summaries **may also reflect other similarity dimensions** when they are present and meaningful (for example shared key/scale, structural traits, automation, or marker activity). When some dimensions are missing for many members, the UI **clearly indicates** partial or missing metadata rather than implying certainty.

**Why this priority**: Browsing the tree is how users act on the grouping.

**Independent Test**: Expand a branch and verify listed projects match the described group; collapse and expand without losing state until the user refreshes or leaves.

**Acceptance Scenarios**:

1. **Given** a populated tree, **When** the user expands a branch, **Then** they see the list of projects in that branch.
2. **Given** a populated tree, **When** the user collapses a branch, **Then** member projects are hidden until expanded again.
3. **Given** a group where a non-tempo dimension (for example key or structural pattern) is shared by a clear majority of members, **When** the user reads the group summary or tooltip, **Then** they can infer at least one such dimension without relying on raw IDs alone (when that data exists in the cluster).

---

### User Story 3 - Scope and refresh (Priority: P3)

The producer limits the tree to a subset of their library (for example projects matching the current filter or selection) and refreshes the tree after the library changes.

**Why this priority**: Improves usefulness on large libraries but is not required for an initial valuable slice.

**Independent Test**: Apply a scope that excludes some projects; tree only includes scoped projects. Trigger refresh; tree updates to match current data.

**Acceptance Scenarios**:

1. **Given** a scope control is available, **When** the user applies a narrower scope, **Then** the tree rebuilds using only projects in that scope.
2. **Given** new projects were indexed since the tree was opened, **When** the user requests a refresh, **Then** the tree reflects the updated set of projects.

---

### Edge Cases

- **No or one project**: The view shows an empty state or a single-node explanation instead of a misleading multi-branch tree.
- **Missing tempo or missing plugin/device lists**: Grouping still runs using available fields; the UI indicates when similarity is partial (for example missing tempo).
- **Very large libraries**: The view remains responsive; if full-library grouping is too heavy, the system may require scope or sampling with a clear message (exact strategy in planning).
- **Duplicate or unknown plugin names**: Projects still appear; naming quirks do not crash the view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST build similarity groups using only project metadata already stored for indexed projects (no requirement to open original project files for the default tree experience).
- **FR-002**: The grouping MUST weight tempo similarity higher than plugin and device overlap when determining which projects belong in the same branch versus a different branch.
- **FR-003**: The grouping MUST incorporate plugin and device overlap as secondary signals so that projects with common tools cluster when tempos are compatible.
- **FR-008**: Group summaries MUST surface human-readable information beyond raw identifiers; they MUST remain honest when metadata is partial (for example missing tempo or sparse feature vectors), consistent with User Story 2.
- **FR-004**: The system MUST present groups as a hierarchical tree with branches and child projects that users can expand and collapse.
- **FR-005**: The system MUST not modify, move, or delete user project files as part of computing or displaying the tree.
- **FR-006**: When metadata is insufficient to form multiple meaningful groups, the system MUST show a clear message or simplified layout instead of an empty or broken view.
- **FR-007**: Users MUST be able to open at least one project from a branch (for example via existing open or reveal actions) without leaving the app.

### Key Entities *(include if feature involves data)*

- **Similarity group (branch)**: A cluster of projects judged similar under the stated weighting; appears as a node in the tree.
- **Project reference**: An indexed project participating in the tree; carries display name and link to existing project actions.
- **Tree scope**: The subset of the library included when building the tree (full library or filtered subset).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a library of up to 5,000 projects, users see a rendered tree within 10 seconds of opening the view under typical use (cold open after indexing is complete).
- **SC-002**: In user-facing acceptance tests, at least 90% of participants can expand a branch and name one other project in the same group without assistance.
- **SC-003**: In structured review sessions, reviewers agree that very different tempos usually produce separate branches even when plugins overlap, and similar tempos more often land in the same branch when plugins also overlap (measured with a short fixed checklist of example pairs).
- **SC-004**: If grouping fails or data is missing, 100% of such cases show a user-visible explanation or fallback layout rather than a blank screen or silent failure.
- **SC-005** *(qualitative)*: In review, users can name at least one **non-tempo** similarity cue from a group summary or tooltip when that dimension is present and shared across a majority of members in that group (for example key, automation-heavy, or typical track counts).
