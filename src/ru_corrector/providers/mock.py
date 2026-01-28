"""Mock provider for testing."""

from ..core.models import TextEdit
from . import CorrectionProvider


class MockProvider(CorrectionProvider):
    """Mock correction provider that returns predefined edits."""

    def __init__(self, edits: list[TextEdit] | None = None):
        """
        Initialize mock provider.
        
        Args:
            edits: Predefined edits to return (defaults to empty list)
        """
        self.edits = edits or []

    def check(self, text: str) -> list[TextEdit]:
        """
        Return predefined edits.
        
        Args:
            text: Text to check (ignored)
            
        Returns:
            Predefined list of edits
        """
        return self.edits.copy()
