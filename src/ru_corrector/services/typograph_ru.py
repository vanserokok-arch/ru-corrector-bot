"""Russian typography rules."""

import re

NBSP = "\u00a0"


def typograph(text: str) -> str:
    """
    Apply Russian typography rules:
    - Convert ... to …
    - Add non-breaking spaces with numbers and units
    - Add non-breaking spaces with №, ст., п., пп., ч., г.
    """
    t = text
    # ... → …
    t = re.sub(r"\.\.\.", "…", t)
    # % and units
    t = re.sub(r"(\d)\s*%", rf"\1{NBSP}%", t)
    t = re.sub(
        r"(\d)\s+(кг|г|м|км|см|мм|л|мл|шт|тыс\.|млн|млрд)", rf"\1{NBSP}\2", t, flags=re.IGNORECASE
    )
    # № and references like ст. 10, п. 3, пп. 2, ч. 1, г. 2025
    t = re.sub(r"№\s+([0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё/-]*)", rf"№{NBSP}\1", t)
    t = re.sub(r"\b(ст|пп|п|ч|г)\.\s*(\d+(?:\.\d+)*)", rf"\1.{NBSP}\2", t, flags=re.IGNORECASE)
    t = re.sub(r"(\d)\s*руб\.", rf"\1{NBSP}руб.", t, flags=re.IGNORECASE)
    # Clean double spaces
    t = re.sub(r" {2,}", " ", t)
    return t
