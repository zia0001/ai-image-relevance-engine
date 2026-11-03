def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors that are already length 1 (see normalize()).
    For length-1 vectors it is just the dot product."""
    return sum(x * y for x, y in zip(a, b))
