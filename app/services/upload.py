import os
from typing import Optional

# only accept csv and json for now
ALLOWED_EXTENSIONS = {".csv", ".json"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/json",
    "application/vnd.ms-excel",
}


def validate_upload(
    filename: str, mime_type: str, max_size_mb: int = 5
) -> tuple[bool, Optional[str]]:
    """Check if an uploaded file is safe. Returns (ok, error_message)."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not allowed. Only CSV and JSON."

    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type '{mime_type}' not recognized."

    if os.path.exists(filename):
        size = os.path.getsize(filename)
        if size > max_size_mb * 1024 * 1024:
            return False, f"File exceeds {max_size_mb} MB."

    if _looks_like_script(filename, ext):
        return False, "File content doesn't match its extension."

    return True, None


def _looks_like_script(filepath: str, ext: str) -> bool:
    """Sniff file header for script-like content."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            head = f.read(512)
        if "#!" in head and ext in (".csv", ".json"):
            return True
        if head.strip().startswith(("<script", "<?php", "import os")):
            return True
    except Exception:
        return True
    return False
