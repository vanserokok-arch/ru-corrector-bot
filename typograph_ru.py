# typograph_ru.py
import re

NBSP = "\u00A0"

def typograph(text: str) -> str:
    t = text
    # ... → …
    t = re.sub(r"\.\.\.", "…", t)
    # % и ед. измерения
    t = re.sub(r"(\d)\s*%", rf"\1{NBSP}%", t)
    t = re.sub(r"(\d)\s+(кг|г|м|км|см|мм|л|мл|шт|тыс\.|млн|млрд)",
               rf"\1{NBSP}\2", t, flags=re.IGNORECASE)
    # № и ссылки вида ст. 10, п. 3, г. 2025
    t = re.sub(r"№\s*(\d)", rf"№{NBSP}\1", t)
    t = re.sub(r"\b(ст|п|г)\.\s*(\d+)", rf"\1.{NBSP}\2", t, flags=re.IGNORECASE)
    # чистим двойные пробелы
    t = re.sub(r" {2,}", " ", t)
    return t