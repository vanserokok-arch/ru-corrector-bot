"""Provider interface and base classes."""

from abc import ABC, abstractmethod

from ..core.models import TextEdit


class CorrectionProvider(ABC):
    """Base interface for correction providers."""

    @abstractmethod
    def check(self, text: str) -> list[TextEdit]:
        """
        Check text and return list of suggested edits.
        
        Args:
            text: Text to check
            
        Returns:
            List of TextEdit objects with suggested corrections
        """
        pass
