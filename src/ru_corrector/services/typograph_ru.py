"""Russian typography rules."""

import re

NBSP = "\u00a0"


def typograph(text: str) -> str:
    """
    Apply Russian typography rules:
    - Convert ... to …
    - Add non-breaking spaces with numbers and units
    - Add non-breaking spaces with №, ст., п., г.
    """
    t = text
    # ... → …
    t = re.sub(r"\.\.\.", "…", t)
    # % and units
    t = re.sub(r"(\d)\s*%", rf"\1{NBSP}%", t)
    t = re.sub(
        r"(\d)\s+(кг|г|м|км|см|мм|л|мл|шт|тыс\.|млн|млрд)", rf"\1{NBSP}\2", t, flags=re.IGNORECASE
    )
    # № and references like ст. 10, п. 3, г. 2025
    t = re.sub(r"№\s*(\d)", rf"№{NBSP}\1", t)
    t = re.sub(r"\b(ст|п|г)\.\s*(\d+)", rf"\1.{NBSP}\2", t, flags=re.IGNORECASE)
    # Clean double spaces
    t = re.sub(r" {2,}", " ", t)
    return t
