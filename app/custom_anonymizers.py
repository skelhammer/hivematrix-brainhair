"""
Custom anonymization operators for Presidio.

This module provides custom anonymizers that format data in specific ways,
such as converting full names to "FirstName L." format.
"""

from presidio_anonymizer.operators import Operator, OperatorType
from typing import Dict
import re


class FirstNameLastInitialOperator(Operator):
    """
    Anonymizes person names to FirstName L. format.

    Example: "John Smith" -> "John S."
    """

    OPERATOR_NAME = "first_name_last_initial"
    OPERATOR_TYPE = OperatorType.Anonymize

    def operate(self, text: str, params: Dict = None) -> str:
        """
        Convert full name to FirstName L. format.

        Args:
            text: The full name text
            params: Optional parameters (not used)

        Returns:
            Formatted name as "FirstName L."
        """
        if not text or not text.strip():
            return text

        # Split the name into parts
        parts = text.strip().split()

        if len(parts) == 0:
            return text
        elif len(parts) == 1:
            # Only first name, return as is
            return parts[0]
        else:
            # First name + last initial
            first_name = parts[0]
            last_initial = parts[-1][0].upper() if parts[-1] else ""
            return f"{first_name} {last_initial}."

    def validate(self, params: Dict = None) -> None:
        """Validate operator parameters (none required)."""
        pass

    def operator_name(self) -> str:
        """Return the operator name."""
        return self.OPERATOR_NAME

    def operator_type(self) -> OperatorType:
        """Return the operator type."""
        return self.OPERATOR_TYPE
