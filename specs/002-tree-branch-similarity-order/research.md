# Research: Similarity Tree — branch member ordering

## 1. Parity with Similarities

**Decision**: Use `SimilarityAnalyzer.compute_similarity(reference_dict, candidate_dict)` for each member vs the branch **anchor** project dictionary. This matches the core of `find_similar_projects`, which ranks candidates against one reference project.

**Rationale**: Spec FR-003 requires the same definition of similarity as the Similarities feature.

## 2. Branch anchor

**Decision (default)**: Choose **medoid** — the member project that minimizes the sum (or mean) of dissimilarity to all other members in the branch, using `1.0 - overall_similarity` as distance. If the branch has one project, that project is the anchor.

**Alternatives**: Centroid of feature vectors only (inconsistent when vectors missing); arbitrary first member (faster but weaker parity story).

## 3. Self-similarity

**Decision**: The anchor project row shows **100%** (or `int(1.0 * 100)`); other members show `compute_similarity(anchor, member)`.

## 4. Tie-break

**Decision**: Sort by `(-overall_similarity, project_name.lower(), project_id)` for deterministic order (FR-006, US2).

## 5. Missing scores

**Decision**: If `compute_similarity` cannot produce a valid score, show a non-numeric fallback in the label (FR-005); still sort with `similarity = -1.0` or push to bottom with stable secondary sort.
