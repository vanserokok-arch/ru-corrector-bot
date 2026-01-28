"""HTML diff view generator."""

import difflib
from html import escape


def make_diff(src: str, dst: str) -> str:
    """
    Create HTML diff view showing changes between source and destination text.

    Args:
        src: Original text
        dst: Corrected text

    Returns:
        HTML string with highlighted changes
    """
    sm = difflib.SequenceMatcher(a=src, b=dst)
    parts = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(escape(dst[j1:j2]))
        elif tag == "insert":
            parts.append(f"<mark style='background:#e6ffed'>{escape(dst[j1:j2])}</mark>")
        elif tag == "delete":
            parts.append(
                f"<mark style='background:#ffeef0;text-decoration:line-through'>"
                f"{escape(src[i1:i2])}</mark>"
            )
        elif tag == "replace":
            parts.append(
                f"<mark style='background:#ffeef0;text-decoration:line-through'>"
                f"{escape(src[i1:i2])}</mark>"
            )
            parts.append(f"<mark style='background:#e6ffed'>{escape(dst[j1:j2])}</mark>")

    return "".join(parts)
