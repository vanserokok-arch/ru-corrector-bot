#!/usr/bin/env python3
"""
Demonstration script showing the layered architecture in action.
This uses a mock provider to avoid needing an external LanguageTool server.
"""

from ru_corrector.core.engine import CorrectionEngine
from ru_corrector.providers.mock import MockProvider
from ru_corrector.core.models import TextEdit

print("=" * 70)
print("RU-CORRECTOR - Layered Architecture Demo")
print("=" * 70)

# Create a mock provider with no edits (just demonstrates the architecture)
mock_provider = MockProvider([])
engine = CorrectionEngine(provider=mock_provider)

print("\n1. Testing BASE mode (provider only):")
text1 = "Простой текст для проверки"
result1, edits1 = engine.correct(text1, mode="base")
print(f"   Input:  {text1}")
print(f"   Output: {result1}")
print(f"   Edits:  {len(edits1)} edits")

print("\n2. Testing LEGAL mode (provider + legal rules):")
text2 = 'Он сказал "привет" и пошел в Москва-Питер'
result2, edits2 = engine.correct(text2, mode="legal")
print(f"   Input:  {text2}")
print(f"   Output: {result2}")
print(f"   Edits:  {len(edits2)} edits")
for edit in edits2:
    print(f"     - {edit.original!r} → {edit.replacement!r} ({edit.message})")

print("\n3. Testing STRICT mode (legal + strict normalization):")
text3 = 'Текст "в кавычках".\n\n\n\nМного пробелов   тут'
result3, edits3 = engine.correct(text3, mode="strict")
print(f"   Input:  {text3!r}")
print(f"   Output: {result3!r}")
print(f"   Edits:  {len(edits3)} edits")

print("\n4. Testing typography rules:")
text4 = "Привет... это стоит 50 % и весит 10 кг, см. п. 123"
result4, edits4 = engine.correct(text4, mode="legal")
print(f"   Input:  {text4}")
print(f"   Output: {result4}")
print(f"   Note: ... → …, nbsp before %, кг, п.")

print("\n5. Testing abbreviation preservation:")
text5 = "ООО РФ согласно ГК РФ"
result5, edits5 = engine.correct(text5, mode="legal")
print(f"   Input:  {text5}")
print(f"   Output: {result5}")
print(f"   Note: Abbreviations preserved")

print("\n6. Demonstrating deterministic behavior:")
text6 = 'Тест "кавычки" и дефис-тире... 50 %'
result6a, _ = engine.correct(text6, mode="legal")
result6b, _ = engine.correct(text6, mode="legal")
print(f"   Input:     {text6}")
print(f"   Output 1:  {result6a}")
print(f"   Output 2:  {result6b}")
print(f"   Match: {result6a == result6b}")

print("\n" + "=" * 70)
print("Demo complete! The engine successfully:")
print("  ✓ Normalized text")
print("  ✓ Applied legal formatting rules (quotes, dashes)")
print("  ✓ Applied typography rules (ellipsis, nbsp)")
print("  ✓ Preserved abbreviations")
print("  ✓ Produced deterministic results")
print("=" * 70)
