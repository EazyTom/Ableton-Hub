# Feature Specification: Similarity Tree — ordered branch members with scores

**Feature Branch**: `002-tree-branch-similarity-order`  
**Created**: 2026-03-22  
**Status**: Draft  
**Input**: User description: "In Similarity Tree, list similarity projects in order of similarity to the tree branch, put the similarity % before the name, like the Similarities window that lists projects % similar to a particular selected project - use the same algorithm"

## Assumptions

- The product already has a **Similarities** experience (or equivalent) that shows other projects ranked by how similar they are to a **single selected project**, including an overall **percentage** derived from the same inputs users already trust.
- A **tree branch** (similarity group) contains one or more **project** members. Users expect those members to be ordered so the **closest** matches to the branch appear **first**.
- The **reference** for “similarity to the branch” is a **single logical anchor** for that branch, derived from that branch’s members so that the **same similarity rules and weighting** as the Similarities experience apply—only the anchor differs from picking one manual project.
- Display format for each project row under a branch: **percentage first**, then the project name (for example `72% — My Song`); exact punctuation may follow existing app conventions for the Similarities list.
- This behavior applies to **project rows** under a branch; it does not require changing how groups are formed or how the tree is clustered.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See branch members sorted by closeness (Priority: P1)

A producer expands a branch in the Similarity Tree and sees **every project in that branch listed in order from most similar to least similar to that branch**, with a **similarity percentage shown before each project name**, using the **same kind of scoring** they already see when they use the Similarities view for a selected project.

**Why this priority**: Ordering and scores turn the branch from an arbitrary list into an actionable “closest first” view.

**Independent Test**: With a branch that has at least three projects, expand it and confirm order is by descending similarity and each row shows a leading percentage plus name.

**Acceptance Scenarios**:

1. **Given** a branch with multiple projects, **When** the user expands the branch, **Then** projects appear **sorted by similarity to that branch** (highest first) and each row shows **percentage before the name**.
2. **Given** the user compares the same project against the same logical reference in both the Similarities experience and under a tree branch, **When** both use the same underlying rules, **Then** the **same overall percentage** (within normal rounding) appears in both places.

---

### User Story 2 - Understand scores and edge cases (Priority: P2)

When some metadata is missing or scores tie, the user still gets a **clear list** without broken ordering or misleading labels.

**Why this priority**: Real libraries have gaps; the list must stay trustworthy.

**Independent Test**: Branches with missing tempo or sparse metadata still show a stable order and readable percentages or an explicit fallback label where a score cannot be computed.

**Acceptance Scenarios**:

1. **Given** two projects with the **same** similarity score to the branch, **When** the list is shown, **Then** the order is **stable** (for example alphabetical by name or project id) so it does not flicker between refreshes.
2. **Given** a project in the branch for which a percentage cannot be computed, **When** the list is shown, **Then** the row still appears with a **clear indication** (for example “—” or “N/A”) instead of a false percentage.

---

### Edge Cases

- **Single project in a branch**: Still shows one row with a meaningful percentage or an explained default.
- **Very small score differences**: Rounded percentages may match; ordering follows underlying score before rounding, or ties are broken as in User Story 2.
- **Large branches**: List remains usable (scrolling is acceptable); performance should not freeze the app while computing order for typical library sizes already supported by Similarities.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Under each expanded **similarity branch**, the system MUST list **project** children in **descending order of similarity to that branch** (most similar first).
- **FR-002**: Each project row MUST show the **overall similarity percentage before the project name**, in line with the user’s requested format and consistent with existing Similarities presentation patterns in the app.
- **FR-003**: The similarity values and ordering MUST use the **same definition of “similarity”** (inputs, weighting, and combination into an overall score) as the existing **Similarities** feature that ranks projects against a **selected** project, adapted only by using the **branch** as the comparison anchor instead of a user-picked project.
- **FR-004**: The system MUST **not** modify, move, or delete user project files solely to compute or display these scores.
- **FR-005**: When metadata is insufficient to compute a score for a member, the system MUST avoid inventing a numeric percentage and MUST surface a **user-visible fallback** on that row.
- **FR-006**: Sorting and labels MUST be **deterministic** for the same data and scope (no random order on repeated refresh).

### Key Entities *(include if feature involves data)*

- **Similarity branch (group node)**: A cluster shown in the tree; provides the anchor context for ordering its project members.
- **Branch member (project row)**: A project listed under that branch; carries display name and computed similarity to the branch.
- **Similarity percentage**: A whole-number (or consistently rounded) display of overall similarity aligned with the Similarities feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability or QA checks, **100%** of tested branches with **three or more** projects show members in **strictly non-increasing** similarity order (ties allowed only with documented tie-break).
- **SC-002**: For a fixed project and comparison context that can be exercised in both this tree view and the Similarities experience, the displayed **percentage matches** within **one percentage point** after rounding.
- **SC-003**: In feedback sessions, **at least 80%** of participants report that “most similar projects appear at the top” of an expanded branch without prompting.
- **SC-004**: No tested case shows a **numeric percentage** where the system has **no valid** similarity computation (fallback required).
