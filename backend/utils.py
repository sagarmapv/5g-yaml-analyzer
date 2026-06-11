from pathlib import Path


def safe_filename(filename: str) -> str | None:
    """Return basename if safe, else None (blocks path traversal)."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return None
    base = Path(filename).name
    if base != filename:
        return None
    return base
