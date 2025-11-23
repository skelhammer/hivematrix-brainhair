"""
Presidio-based PHI/CJIS data anonymization module.

This module provides functions to detect and anonymize sensitive information
in text data before exposing it through APIs. It handles PHI (Protected Health
Information) and CJIS (Criminal Justice Information Systems) data.
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import Dict, List, Any, Optional
import json
import os
import sys

# Import custom anonymizers without triggering app/__init__.py
sys.path.insert(0, os.path.dirname(__file__))
from custom_anonymizers import FirstNameLastInitialOperator

class PresidioFilter:
    """
    Manages PHI/CJIS data filtering using Microsoft Presidio.

    This class initializes Presidio analyzers and anonymizers to detect
    and redact sensitive information from text data.
    """

    def __init__(self):
        """Initialize Presidio analyzer and anonymizer engines."""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # Register custom anonymizers
        self.anonymizer.add_anonymizer(FirstNameLastInitialOperator)

        # Define entity types to detect

        # CRITICAL: High-security entities (financial/government IDs only)
        # Use this for MSP internal tools where operational data is needed
        self.critical_entities = [
            "US_SSN",              # Social Security Numbers
            "CREDIT_CARD",         # Credit card numbers
            "IBAN_CODE",           # Bank account numbers
            "US_PASSPORT",         # Passport numbers
            "US_DRIVER_LICENSE",   # Driver's license numbers
        ]

        # PHI entities (healthcare context - overly aggressive for MSP)
        # Only use if supporting healthcare clients with actual PHI in tickets
        self.phi_entities = [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "US_SSN",
            # "DATE_TIME",  # Excluded - dates are operational data in ticketing context
            "LOCATION",
            "MEDICAL_LICENSE",
            "US_DRIVER_LICENSE",
            "US_PASSPORT",
            "CREDIT_CARD",
            "IBAN_CODE",
            "IP_ADDRESS",
            "NRP"  # National Registry Provider (medical)
        ]

        # CJIS additional entities
        self.cjis_entities = [
            "PERSON",
            "US_SSN",
            "US_DRIVER_LICENSE",
            # "DATE_TIME",  # Excluded - dates are operational data in ticketing context
            "LOCATION",
            "IP_ADDRESS"
        ]

        # Default to critical_entities for MSP use (minimal redaction)
        self.default_entities = self.critical_entities

    def analyze_text(self, text: str, entity_types: Optional[List[str]] = None) -> List:
        """
        Analyze text to find sensitive entities.

        Args:
            text: The text to analyze
            entity_types: List of entity types to detect (defaults to critical entities)

        Returns:
            List of detected entities with their locations and scores
        """
        if entity_types is None:
            entity_types = self.default_entities

        results = self.analyzer.analyze(
            text=text,
            language='en',
            entities=entity_types
        )

        return results

    def anonymize_text(self, text: str, entity_types: Optional[List[str]] = None,
                      anonymization_type: str = "replace") -> str:
        """
        Anonymize sensitive information in text.

        Args:
            text: The text to anonymize
            entity_types: List of entity types to anonymize (defaults to critical entities)
            anonymization_type: Type of anonymization ("replace", "mask", "redact", "hash")

        Returns:
            Anonymized text with sensitive information replaced
        """
        if entity_types is None:
            entity_types = self.default_entities

        # Analyze the text first
        results = self.analyze_text(text, entity_types)

        # Define anonymization operators
        operators = {}
        if anonymization_type == "replace":
            # Use custom anonymizer for PERSON entities (FirstName L. format)
            # Replace other entities with type labels
            operators = {}
            for entity in entity_types:
                if entity == "PERSON":
                    operators[entity] = OperatorConfig("first_name_last_initial", {})
                else:
                    operators[entity] = OperatorConfig("replace", {"new_value": f"<{entity}>"})
        elif anonymization_type == "mask":
            # Mask with asterisks
            operators = {entity: OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 100, "from_end": False})
                        for entity in entity_types}
        elif anonymization_type == "redact":
            # Remove completely
            operators = {entity: OperatorConfig("redact", {})
                        for entity in entity_types}
        elif anonymization_type == "hash":
            # Hash the values
            operators = {entity: OperatorConfig("hash", {})
                        for entity in entity_types}

        # Anonymize the text
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )

        return anonymized_result.text

    def filter_dict(self, data: Dict[str, Any], fields_to_filter: Optional[List[str]] = None,
                   entity_types: Optional[List[str]] = None,
                   anonymization_type: str = "replace") -> Dict[str, Any]:
        """
        Filter sensitive information from a dictionary.

        Args:
            data: Dictionary to filter
            fields_to_filter: List of field names to filter (if None, filters all string fields)
            entity_types: List of entity types to detect (defaults to critical entities)
            anonymization_type: Type of anonymization

        Returns:
            Filtered dictionary with sensitive information anonymized
        """
        if entity_types is None:
            entity_types = self.default_entities

        filtered_data = data.copy()

        for key, value in filtered_data.items():
            # Skip if we have a specific field list and this field isn't in it
            if fields_to_filter and key not in fields_to_filter:
                continue

            if isinstance(value, str):
                filtered_data[key] = self.anonymize_text(value, entity_types, anonymization_type)
            elif isinstance(value, dict):
                filtered_data[key] = self.filter_dict(value, fields_to_filter, entity_types, anonymization_type)
            elif isinstance(value, list):
                filtered_data[key] = [
                    self.filter_dict(item, fields_to_filter, entity_types, anonymization_type)
                    if isinstance(item, dict)
                    else self.anonymize_text(item, entity_types, anonymization_type)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]

        return filtered_data

    def filter_list(self, data: List[Any], fields_to_filter: Optional[List[str]] = None,
                   entity_types: Optional[List[str]] = None,
                   anonymization_type: str = "replace") -> List[Any]:
        """
        Filter sensitive information from a list.

        Args:
            data: List to filter
            fields_to_filter: List of field names to filter in dict items
            entity_types: List of entity types to detect (defaults to critical entities)
            anonymization_type: Type of anonymization

        Returns:
            Filtered list with sensitive information anonymized
        """
        if entity_types is None:
            entity_types = self.default_entities

        filtered_list = []
        for item in data:
            if isinstance(item, dict):
                filtered_list.append(self.filter_dict(item, fields_to_filter, entity_types, anonymization_type))
            elif isinstance(item, str):
                filtered_list.append(self.anonymize_text(item, entity_types, anonymization_type))
            else:
                filtered_list.append(item)

        return filtered_list

    def filter_phi(self, data: Any, fields_to_filter: Optional[List[str]] = None) -> Any:
        """
        Filter PHI (Protected Health Information) from data.

        NOTE: Uses critical_entities (minimal redaction) by default.
        For full PHI compliance, use filter_dict/filter_list with self.phi_entities.

        Args:
            data: Data to filter (dict, list, or str)
            fields_to_filter: List of field names to filter (for dict/list of dicts)

        Returns:
            Filtered data with critical entities anonymized
        """
        if isinstance(data, dict):
            return self.filter_dict(data, fields_to_filter, self.default_entities)
        elif isinstance(data, list):
            return self.filter_list(data, fields_to_filter, self.default_entities)
        elif isinstance(data, str):
            return self.anonymize_text(data, self.default_entities)
        else:
            return data

    def filter_cjis(self, data: Any, fields_to_filter: Optional[List[str]] = None) -> Any:
        """
        Filter CJIS (Criminal Justice Information Systems) data from data.

        Args:
            data: Data to filter (dict, list, or str)
            fields_to_filter: List of field names to filter (for dict/list of dicts)

        Returns:
            Filtered data with CJIS information anonymized
        """
        if isinstance(data, dict):
            return self.filter_dict(data, fields_to_filter, self.cjis_entities)
        elif isinstance(data, list):
            return self.filter_list(data, fields_to_filter, self.cjis_entities)
        elif isinstance(data, str):
            return self.anonymize_text(data, self.cjis_entities)
        else:
            return data


# Global instance for easy import
_presidio_filter = None

def get_presidio_filter() -> PresidioFilter:
    """Get or create the global Presidio filter instance."""
    global _presidio_filter
    if _presidio_filter is None:
        _presidio_filter = PresidioFilter()
    return _presidio_filter


def filter_data(data: Any, fields_to_filter: Optional[List[str]] = None) -> Any:
    """
    Convenience function to filter sensitive data (minimal redaction).

    Uses critical_entities (SSN, credit cards, passports, driver's licenses, bank accounts)
    by default. Does NOT redact operational business data (names, emails, phones, addresses).

    For full PHI compliance (healthcare context), use:
        filter_instance.filter_dict(data, fields_to_filter, filter_instance.phi_entities)

    Args:
        data: Data to filter (dict, list, or str)
        fields_to_filter: List of field names to filter (for dict/list of dicts)

    Returns:
        Filtered data with critical entities anonymized
    """
    filter_instance = get_presidio_filter()
    return filter_instance.filter_phi(data, fields_to_filter)


def filter_by_compliance_level(data: Any, compliance_level: str = 'standard',
                                fields_to_filter: Optional[List[str]] = None) -> Any:
    """
    Filter data based on company compliance level.

    Args:
        data: Data to filter (dict, list, or str)
        compliance_level: Compliance level ('standard', 'cjis', 'phi')
        fields_to_filter: List of field names to filter (for dict/list of dicts)

    Returns:
        Filtered data with appropriate entities anonymized based on compliance level

    Compliance levels:
        - standard: Minimal filtering (SSN, credit cards, passports, licenses, bank accounts)
        - cjis: Criminal justice filtering (PERSON, SSN, DRIVER_LICENSE, LOCATION, IP_ADDRESS, DATE_TIME)
        - phi: Healthcare filtering (all PII/PHI including names, emails, phones, medical data)
    """
    filter_instance = get_presidio_filter()

    # Map compliance level to entity list
    if compliance_level == 'cjis':
        entity_list = filter_instance.cjis_entities
    elif compliance_level == 'phi':
        entity_list = filter_instance.phi_entities
    else:  # 'standard' or any other value defaults to standard
        entity_list = filter_instance.critical_entities

    # Apply filtering with the appropriate entity list
    if isinstance(data, dict):
        return filter_instance.filter_dict(data, fields_to_filter, entity_list)
    elif isinstance(data, list):
        return filter_instance.filter_list(data, fields_to_filter, entity_list)
    elif isinstance(data, str):
        return filter_instance.anonymize_text(data, entity_list)
    else:
        return data
