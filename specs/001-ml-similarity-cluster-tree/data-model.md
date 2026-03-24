# Data Model: Similarity Cluster Tree View

Logical entities for this feature (not necessarily 1:1 DB tables).

## ProjectReference

| Field | Description |
|-------|-------------|
| `id` | Existing `Project.id` |
| `display_name` | `Project.name` (or export title if product prefers) |
| `tempo` | `Project.tempo` (nullable) |
| `plugins` | List from `Project.plugins` JSON |
| `devices` | List from `Project.devices` JSON |

**Source**: Loaded via `ProjectRepository` / session queries; no new table required for MVP.

## TreeScope

Represents **User Story 3** filters (optional for MVP).

| Field | Description |
|-------|-------------|
| `location_id` | Optional filter |
| `collection_id` | Optional filter |
| `tag_id` | Optional filter |
| `search_query` | Optional text filter |
| `tempo_min` / `tempo_max` | Optional range |

**Mapping**: Passed through to `ProjectRepository.get_all` parameters where applicable.

## SimilarityGroupNode (internal / UI model)

| Field | Description |
|-------|-------------|
| `node_id` | Stable string or int within tree build session |
| `label` | Human-readable summary (tempo band + shared tools) |
| `children` | List of child nodes (nested groups or projects) |
| `project_ids` | Projects contained in this subtree (for summaries) |

## SimilarityTreeResult

Worker output consumed by the UI thread.

| Field | Description |
|-------|-------------|
| `root_nodes` | Top-level `SimilarityGroupNode` list (or single root) |
| `project_rows` | Map `project_id` → display fields for leaves |
| `warnings` | e.g. “partial tempo data”, “sampled 5000 of 12000” |
| `computed_at` | Timestamp |
| `parameters` | Heuristic `n_clusters`, weights version string |

**Persistence**: Ephemeral (in-memory); no requirement to store tree in DB for MVP unless product later wants caching.

## Validation rules

- Leaves reference only **existing** `project_id` values from the current scope query.
- If `n &lt; 2`, return empty state / message (spec edge cases) instead of invalid multi-branch tree.
