"""Fixtures for tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_languagetool(monkeypatch):
    """Mock LanguageTool to avoid external API calls in tests."""

    class MockMatch:
        """Mock LanguageTool match."""

        def __init__(self, offset, length, replacements):
            self.offset = offset
            self.errorLength = length
            self.replacements = [Mock(value=r) for r in replacements]

    class MockMatches:
        """Mock LanguageTool matches."""

        def __init__(self, matches):
            self.matches = matches

    class MockLanguageTool:
        """Mock LanguageTool client."""

        def check(self, text):
            # Return empty matches for most text
            # Add specific rules for test cases if needed
            return MockMatches([])

        def close(self):
            pass

    # Mock the _get_languagetool function
    mock_lt = MockLanguageTool()

    def mock_get_lt():
        return mock_lt

    # Patch the module
    import ru_corrector.services.core_corrector as corrector_module

    monkeypatch.setattr(corrector_module, "_get_languagetool", mock_get_lt)

    return mock_lt
