from __future__ import annotations

from backend.models.dto import OrderInput
from backend.services.freight_distribution import FreightDistributionService, FreightDistributionResult
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.xml_import_service import XmlImportService, XmlImportResult


class BusinessHandler:
    """Handles all business-logic operations for the QML layer."""

    def __init__(
        self,
        validation: ValidationService,
        freight: FreightDistributionService,
        xml_import: XmlImportService,
    ) -> None:
        self._validation = validation
        self._freight = freight
        self._xml_import = xml_import

    def distribute_freight(self, order_input: OrderInput) -> FreightDistributionResult:
        """Distribute freight costs across products in an order."""
        return self._freight.distribute(order_input)

    def import_xml(self, file_path: str) -> XmlImportResult:
        """Import data from an NFe XML file."""
        return self._xml_import.parse_file(file_path)

    def validate_order(self, order_input: OrderInput) -> ValidationResult:
        """Validate an order and return the result."""
        return self._validation.validate_order(order_input)

    def validate_expense(self, description: str, value: int) -> ValidationResult:
        """Validate a single expense."""
        return self._validation.validate_expense(description, value)
