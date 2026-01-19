"""Fuzzy string matching utilities for export detection and project matching."""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from rapidfuzz import fuzz, process


@dataclass
class MatchResult:
    """Result of a fuzzy match operation."""
    matched_text: str
    score: float
    index: int


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate the similarity score between two strings.
    
    Uses a weighted combination of different fuzzy matching algorithms
    for better accuracy with file names.
    
    Args:
        str1: First string.
        str2: Second string.
        
    Returns:
        Similarity score from 0 to 100.
    """
    # Normalize strings for comparison
    s1 = normalize_for_comparison(str1)
    s2 = normalize_for_comparison(str2)
    
    # Weight different similarity measures
    ratio = fuzz.ratio(s1, s2)
    partial = fuzz.partial_ratio(s1, s2)
    token_sort = fuzz.token_sort_ratio(s1, s2)
    token_set = fuzz.token_set_ratio(s1, s2)
    
    # Weighted average favoring token-based matching for file names
    return (ratio * 0.2 + partial * 0.2 + token_sort * 0.3 + token_set * 0.3)


def normalize_for_comparison(text: str) -> str:
    """Normalize a string for fuzzy comparison.
    
    Removes common suffixes, version numbers, and standardizes separators.
    
    Args:
        text: The string to normalize.
        
    Returns:
        Normalized string.
    """
    import re
    
    # Convert to lowercase
    result = text.lower()
    
    # Remove file extension
    result = re.sub(r'\.(als|wav|mp3|flac|aiff|aif)$', '', result, flags=re.IGNORECASE)
    
    # Remove common suffixes
    suffixes = [
        r'_final$', r'_master$', r'_mix$', r'_bounce$', r'_export$',
        r' final$', r' master$', r' mix$', r' bounce$', r' export$',
        r'_project$', r' project$',  # "project" suffix
        r'_v\d+$', r' v\d+$', r'_\d+$',  # Version numbers
        r'[-_]\d{4}[-_]\d{2}[-_]\d{2}.*$',  # Date stamps like _2024-01-15
    ]
    for suffix in suffixes:
        result = re.sub(suffix, '', result, flags=re.IGNORECASE)
    
    # Remove "project" anywhere in the string (common in Ableton naming)
    result = re.sub(r'\bproject\b', '', result, flags=re.IGNORECASE)
    
    # Standardize separators
    result = re.sub(r'[-_\s]+', ' ', result)
    
    # Remove extra whitespace
    result = ' '.join(result.split())
    
    return result.strip()


def fuzzy_match_projects(
    query: str,
    project_names: List[str],
    threshold: float = 60.0,
    limit: int = 10
) -> List[MatchResult]:
    """Find projects that fuzzy match a query string.
    
    Args:
        query: The search query.
        project_names: List of project names to search.
        threshold: Minimum similarity score (0-100).
        limit: Maximum number of results to return.
        
    Returns:
        List of MatchResult objects sorted by score descending.
    """
    if not query or not project_names:
        return []
    
    normalized_query = normalize_for_comparison(query)
    
    # Use rapidfuzz process.extract for efficient batch matching
    results = process.extract(
        normalized_query,
        [normalize_for_comparison(name) for name in project_names],
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=threshold
    )
    
    return [
        MatchResult(
            matched_text=project_names[result[2]],
            score=result[1],
            index=result[2]
        )
        for result in results
    ]


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: float = 70.0
) -> Optional[MatchResult]:
    """Find the single best matching candidate for a query.
    
    Args:
        query: The search query.
        candidates: List of candidate strings.
        threshold: Minimum similarity score required.
        
    Returns:
        MatchResult for best match, or None if no match above threshold.
    """
    matches = fuzzy_match_projects(query, candidates, threshold=threshold, limit=1)
    return matches[0] if matches else None


def match_export_to_project(
    export_name: str,
    project_names: List[str],
    threshold: float = 65.0
) -> List[Tuple[str, float]]:
    """Match an export filename to potential source projects.
    
    Uses specialized matching that accounts for common export naming patterns.
    
    Args:
        export_name: The export filename (without extension).
        project_names: List of project names to match against.
        threshold: Minimum similarity score.
        
    Returns:
        List of (project_name, score) tuples sorted by score descending.
    """
    if not export_name or not project_names:
        return []
    
    # Normalize the export name
    normalized_export = normalize_for_comparison(export_name)
    
    results = []
    for name in project_names:
        normalized_project = normalize_for_comparison(name)
        score = calculate_similarity(normalized_export, normalized_project)
        
        if score >= threshold:
            results.append((name, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def extract_song_name(filename: str) -> str:
    """Extract the likely song name from a filename.
    
    Removes common prefixes, suffixes, version numbers, etc.
    
    Args:
        filename: The filename to process.
        
    Returns:
        Extracted song name.
    """
    import re
    
    # Remove extension
    name = re.sub(r'\.[^.]+$', '', filename)
    
    # Remove track number prefixes (01 -, 01_, 01., etc.)
    name = re.sub(r'^(\d{1,2}[\s._-]+)', '', name)
    
    # Remove album/artist prefixes if separated by " - "
    parts = name.split(' - ')
    if len(parts) >= 2:
        # Assume last part is the song name if there are multiple parts
        name = parts[-1]
    
    # Remove common suffixes
    suffixes = [
        r'\s*\(.*\)$',  # Parenthetical suffixes
        r'\s*\[.*\]$',  # Bracketed suffixes
        r'_final$', r'_master$', r'_v\d+$',
        r' final$', r' master$', r' v\d+$',
    ]
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    return name.strip()
