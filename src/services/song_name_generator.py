"""Random song name generator for creative project naming."""

import random

# Word lists: sci-fi, futuristic, ancient, shamanism, chemical, creation
# Single-syllable: punchy, strong
_ONE_SYL = [
    "fire",
    "flame",
    "sky",
    "sea",
    "soul",
    "night",
    "light",
    "moon",
    "star",
    "sun",
    "dust",
    "mist",
    "ice",
    "gold",
    "blue",
    "red",
    "glow",
    "spark",
    "wave",
    "tide",
    "storm",
    "bloom",
    "ember",
    "stone",
    "steel",
    "glass",
    "path",
    "road",
    "gate",
    "wall",
    "tower",
    "pulse",
    "beat",
    "rhythm",
    "void",
    "edge",
    "start",
    "core",
    "flux",
    "mesh",
    "node",
    "code",
    "forge",
    "craft",
    "birth",
    "rise",
    "run",
    "hold",
    "call",
    "find",
    "warp",
    "beam",
    "cell",
    "atom",
    "ion",
    "bond",
    "melt",
    "sage",
    "rite",
    "drum",
    "smoke",
    "herb",
    "root",
    "seed",
    "bone",
]

# Two syllables: flowing
_TWO_SYL = [
    # Sci-fi / Futuristic
    "plasma",
    "quantum",
    "nexus",
    "orbit",
    "nebula",
    "pulsar",
    "photon",
    "cyborg",
    "android",
    "nanite",
    "drone",
    "laser",
    "hyper",
    "cyber",
    "neural",
    "digital",
    "neon",
    "synthetic",
    "hybrid",
    "hologram",
    "reactor",
    "vector",
    "matrix",
    "signal",
    "portal",
    "warp",
    "phase",
    # Ancient
    "ancient",
    "oracle",
    "relic",
    "obelisk",
    "pyramid",
    "sphinx",
    "rune",
    "glyph",
    "temple",
    "shrine",
    "altar",
    "cipher",
    "scroll",
    "dragon",
    "phoenix",
    "serpent",
    "falcon",
    "eagle",
    "raven",
    # Shamanism
    "spirit",
    "vision",
    "ritual",
    "totem",
    "sacred",
    "trance",
    "journey",
    "medicine",
    "ancestor",
    "dreamtime",
    "ceremony",
    "drumbeat",
    "chant",
    "crystal",
    "quartz",
    "jade",
    "opal",
    "ember",
    # Chemical / Creation
    "compound",
    "element",
    "fusion",
    "reaction",
    "genesis",
    "emerge",
    "evolve",
    "transform",
    "ignite",
    "forge",
    "echoes",
    "horizons",
    "mountains",
    "rivers",
    "oceans",
    "forests",
    "twilight",
    "sunset",
    "sunrise",
    "crimson",
    "velvet",
    "obsidian",
]

# Three syllables: expansive
_THREE_SYL = [
    # Sci-fi / Futuristic
    "infinity",
    "eternity",
    "synthetic",
    "holographic",
    "electromagnetic",
    "interstellar",
    "hyperdrive",
    "cybernetic",
    "nanotechnology",
    "prototype",
    "paradigm",
    "algorithm",
    # Ancient
    "primordial",
    "archaeic",
    "mysterious",
    "legendary",
    "mythical",
    "cathedral",
    "monastery",
    "sanctuary",
    "monument",
    "artifact",
    # Shamanism
    "visionary",
    "ceremonial",
    "ancestral",
    "elemental",
    "spiritual",
    "transcendent",
    "awakening",
    "transformation",
    "illumination",
    # Chemical / Creation
    "catalyst",
    "synthesis",
    "molecule",
    "transmutation",
    "crystallization",
    "generation",
    "evolution",
    "transmutation",
    "crystallization",
    "symphony",
    "harmony",
    "melody",
    "cascade",
    "waterfall",
    "rainbow",
]

# Short phrases for building longer titles (max 5 syllables total)
_PHRASES = [
    "in the void",
    "in the light",
    "forever",
    "again",
    "part one",
    "part two",
    "reprise",
    "interlude",
    "outro",
    "first light",
    "new dawn",
    "phase one",
    "phase two",
]


# Syllable counts for words (approximate); fallback uses vowel-group heuristic
def _count_syllables(word: str) -> int:
    """Estimate syllable count. Count vowel groups (aeiouy), min 1."""
    word = word.lower()
    if not word:
        return 0
    count = 0
    prev_vowel = False
    for c in word:
        is_vowel = c in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(1, count)


def _total_syllables(name: str) -> int:
    """Total syllable count for a song name."""
    return sum(_count_syllables(w) for w in name.lower().split())


def _pick_word_count() -> int:
    """Return 1-5 with bias toward 2-4 (poetic length)."""
    r = random.random()
    if r < 0.08:
        return 1
    elif r < 0.35:
        return 2
    elif r < 0.65:
        return 3
    elif r < 0.88:
        return 4
    else:
        return 5


def _words_in_name(name: str) -> set[str]:
    """Return set of lowercase words in the name."""
    return set(name.lower().split())


def _has_repeated_words(name: str) -> bool:
    """Return True if the name contains the same word more than once."""
    words = name.lower().split()
    return len(words) != len(set(words))


def _get_available_words(excluded: set[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (one_syl, two_syl, three_syl) lists with excluded words removed."""
    one = [w for w in _ONE_SYL if w not in excluded]
    two = [w for w in _TWO_SYL if w not in excluded]
    three = [w for w in _THREE_SYL if w not in excluded]
    return one, two, three


def generate_song_name(excluded_words: set[str] | None = None) -> str | None:
    """Generate a random song name with 1-5 words and poetic meter.

    Args:
        excluded_words: Words already used in this batch - will not be reused.

    Returns:
        A title-cased song name, or None if invalid (repeated words or no words available).
    """
    excluded = excluded_words or set()
    one, two, three = _get_available_words(excluded)

    word_count = _pick_word_count()

    if word_count == 1:
        pool = one + [w for w in two if len(w) <= 7]
        if not pool:
            return None
        return random.choice(pool).title()

    # Build multi-word name from available pools
    one_pool = one + two[:20]
    two_pool = two + three[:12]
    if not one_pool or not two_pool:
        return None

    words = []
    for i in range(word_count):
        pool = one_pool if i % 2 == 0 else two_pool
        available = [w for w in pool if w not in words]
        if not available:
            return None
        words.append(random.choice(available))

    # Occasionally use a phrase for 3-5 word titles
    if word_count >= 3 and random.random() < 0.2:
        phrase = random.choice(_PHRASES)
        phrase_words = phrase.split()
        if len(phrase_words) <= word_count:
            # Phrase words must not be in excluded or already in words
            used = excluded | set(words)
            if not any(pw in used for pw in phrase_words):
                words = words[: word_count - len(phrase_words)] + phrase_words

    name = " ".join(w.capitalize() for w in words)
    if _has_repeated_words(name):
        return None
    if _total_syllables(name) > 5:
        return None
    return name


def generate_song_names(count: int = 10) -> list[str]:
    """Generate multiple unique song names with no duplicate names or repeated words.

    - No repeated words within a single name
    - No repeated words across the entire batch (each word used at most once)
    - All names are unique

    Args:
        count: Number of names to generate.

    Returns:
        List of unique title-cased song names.
    """
    seen_names: set[str] = set()
    used_words: set[str] = set()
    result: list[str] = []
    attempts = 0
    max_attempts = count * 80

    while len(result) < count and attempts < max_attempts:
        attempts += 1
        name = generate_song_name(excluded_words=used_words)
        if name is None or name in seen_names:
            continue

        words = _words_in_name(name)
        if words & used_words:
            continue  # Would reuse a word from another name

        seen_names.add(name)
        used_words.update(words)
        result.append(name)

    return result
