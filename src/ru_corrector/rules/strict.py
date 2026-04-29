"""Strict correction pipeline."""

from __future__ import annotations

import re

from .legal import apply_legal


def strict_line_cleanup(text: str) -> str:
    """Cleanup each line while preserving line breaks and list structure."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []

    for line in lines:
        body = line.rstrip("\r\n")
        ending = line[len(body) :]

        body = re.sub(r"\s+([.,;:!?])", r"\1", body)
        body = re.sub(r"([.,;:!?])(?=[A-Za-zА-Яа-яЁё])", r"\1 ", body)
        body = re.sub(r"\(\s+", "(", body)
        body = re.sub(r"\s+\)", ")", body)
        body = re.sub(r"«\s+", "«", body)
        body = re.sub(r"\s+»", "»", body)

        body = re.sub(r"!{2,}", "!", body)
        body = re.sub(r"\?{2,}", "?", body)
        body = re.sub(r",{2,}", ",", body)
        body = re.sub(r"\.{3,}", "…", body)

        body = re.sub(r" {2,}", " ", body)
        out.append(body + ending)

    return "".join(out)


def apply_strict(text: str, provider=None) -> str:
    """apply_legal -> strict line cleanup."""
    return strict_line_cleanup(apply_legal(text, provider=provider))
