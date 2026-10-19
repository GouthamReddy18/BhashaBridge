def normalize_whitespace(text: str) -> str:
    """Collapse whitespace runs and trim edges without changing other characters.

    The caller retains the original text separately. `split` treats Unicode
    whitespace consistently and the join inserts one ASCII space between runs.
    """
    return " ".join(text.split())
