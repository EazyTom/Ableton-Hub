<!--
Sync Impact Report — constitution v1.0.0
- Version change: (unfilled template) → 1.0.0
- Principles: placeholders → I. User Project Safety; II. Stack Conformance;
  III. Regression Testing; IV. Responsive UI & Threading; V. Focused Scope
- Added sections: Technology Stack & Platform Constraints; Development Workflow & Quality Gates
- Removed sections: none (template placeholders only)
- Templates: .specify/templates/plan-template.md ✅ | spec-template.md ✅ | tasks-template.md ✅
- .specify/templates/commands/*.md — ⚠ not present (no files to update)
- .cursor/commands/*.md — ✅ reviewed; no CLAUDE-only agent refs found
- Follow-up TODOs: none
-->

# Ableton Hub Constitution

## Core Principles

### I. User Project Safety & Non-Destructive Defaults

Features that read or index user content MUST treat Ableton project files and audio assets as
read-only unless the feature’s explicit purpose is to modify them. The application MUST NOT
silently overwrite, truncate, or corrupt `.als` files or user media. When writing is required,
the spec MUST describe the write path, failure modes, and recovery or rollback behavior.
Parsing and scanning MUST degrade gracefully on partial or future-format files: log actionable
errors, surface a clear user-visible message when appropriate, and avoid crashing the
application. Rationale: users’ creative work is the product’s trust boundary; data loss is
unacceptable.

### II. Stack Conformance

Implementation MUST use the repository’s adopted stack unless a feature specification documents
and justifies an exception in the plan’s Complexity Tracking table. Baseline: Python 3.11 or
newer; PyQt6 for GUI; SQLAlchemy for persistence; type hints on new and materially changed
public APIs; PEP 8 for style. Rationale: consistency reduces review load and defect surface.

### III. Regression Testing (pytest)

Behavioral changes to parsing, indexing, search, database schema, or business logic MUST include
automated tests that would fail under the old behavior, using `pytest` unless the feature spec
explicitly exempts test work. UI-only tweaks MAY rely on manual verification when the spec
states that and the plan records the manual checklist. Rationale: the codebase already relies
on pytest; tests protect `.als` handling and DB migrations from silent regressions.

### IV. Responsive UI & Threading Discipline

Long-running work (full-library scans, heavy similarity computation, bulk I/O) MUST NOT block
the Qt GUI thread. Workers MUST use the project’s established patterns for background execution
and thread-safe signals/slots. UI updates MUST occur on the main thread. Rationale: freezes erode
trust and mimic hangs or crashes on large libraries.

### V. Focused Scope & Traceable Work

Each change set MUST address the stated feature or fix without unrelated refactors or cosmetic
wide edits. Feature plans and tasks MUST trace requirements to user stories and file paths so
reviews can verify completeness. Rationale: small, reviewable diffs reduce merge risk and make
regressions easier to bisect.

## Technology Stack & Platform Constraints

- **Language**: Python 3.11+ with type hints on new public surfaces.
- **UI**: PyQt6; follow existing widget and styling patterns in `src/`.
- **Data**: SQLAlchemy and project migrations as already used in the repo.
- **Primary dev OS**: Windows 10/11; shell automation and contributor docs SHOULD use PowerShell
  conventions consistent with `.cursorrules` (e.g., `venv\Scripts\activate`).
- **External parsing**: Dependencies such as dawtool for `.als` analysis MUST be pinned and
  upgraded deliberately; breaking changes require tests and release notes.

## Development Workflow & Quality Gates

- **Specs**: User scenarios, functional requirements, edge cases, and measurable success
  criteria MUST be filled for feature work using `/speckit.specify` outputs; vague requirements
  MUST be marked `NEEDS CLARIFICATION` until resolved.
- **Plans**: `/speckit.plan` MUST pass the Constitution Check before Phase 0 research and MUST
  be re-checked after Phase 1 design; violations MUST be listed in Complexity Tracking with
  justification or resolved.
- **Tasks**: `/speckit.tasks` MUST group work by user story and reference concrete paths under
  `src/` and `tests/`.
- **Review**: Reviewers MUST confirm principles I–V for relevant changes (safety, stack, tests,
  threading, scope).

## Governance

This constitution supersedes informal coding preferences when they conflict. Amendments MUST be
made via an explicit update to `.specify/memory/constitution.md` (not drive-by edits in feature
specs). **Versioning**: `MAJOR` for incompatible principle removals or redefinitions; `MINOR`
for new principles or materially expanded governance; `PATCH` for clarifications and non-normative
wording. **Amendment procedure**: edit the constitution, bump the version with rationale in the
Sync Impact Report comment, propagate template updates, and merge through the normal review
process. **Compliance**: Feature analysis (`/speckit.analyze`) and implementation MUST treat
constitution `MUST` rules as non-negotiable; conflicts require a constitution change first.
Day-to-day development guidance remains in `.cursorrules` and `README.md` where they do not
contradict this document.

**Version**: 1.0.0 | **Ratified**: 2025-03-22 | **Last Amended**: 2025-03-22
