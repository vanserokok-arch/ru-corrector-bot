"""Fixtures for tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_languagetool(monkeypatch):
    """Mock LanguageTool to avoid external API calls in tests."""

    class MockMatch:
        """Mock LanguageTool match."""

        def __init__(self, offset, length, replacements, message="", rule_id=""):
            self.offset = offset
            self.errorLength = length
            self.replacements = [Mock(value=r) for r in replacements]
            self.message = message
            self.ruleId = rule_id

    class MockLanguageTool:
        """Mock LanguageTool client.

        check() returns a plain list[MockMatch], mirroring the real
        LanguageTool.check() return type.
        """

        def check(self, text):
            # Return empty list for most text
            # Tests that need specific corrections inject their own MockProvider
            return []

        def close(self):
            pass

    # Mock the _get_languagetool function in both modules
    mock_lt = MockLanguageTool()

    def mock_get_lt():
        return mock_lt

    # Patch both the old and new modules
    try:
        import ru_corrector.services.core_corrector as old_corrector
        monkeypatch.setattr(old_corrector, "_get_languagetool", mock_get_lt)
    except (ImportError, AttributeError):
        pass

    try:
        import ru_corrector.providers.languagetool as lt_provider
        monkeypatch.setattr(lt_provider, "_get_languagetool", mock_get_lt)
    except (ImportError, AttributeError):
        pass

    return mock_lt
