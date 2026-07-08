from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from backend.models.dto import ExpenseInput, OrderInput
from backend.utils.date import br_date_to_iso, parse_month_for_orders, parse_month_for_expenses


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ProductValidationResult:
    """Validation result for a single product."""
    valid: bool
    errors: list[str] = field(default_factory=list)


class ValidationService:
    """
    Implements cross-field validation rules for orders, products, and expenses.

    Validation rules (per docs §3.2.8 and Appendix B):
    1. Product: name, quantity, price must all be filled or all empty.
    2. Order: date valid format, supplier required, all products valid.
    3. Expense: description and value required together.
    """

    def validate_product(
        self,
        name: str,
        quantity: int,
        price: int,
    ) -> ProductValidationResult:
        """
        Validate a single product's core fields.

        Rule: name, quantity, price must all be filled or all empty.
        'Filled' means non-empty string (for name) or non-zero (for quantity/price).

        Args:
            name: Product name string.
            quantity: Product quantity (integer).
            price: Product unit price in cents (integer).

        Returns:
            ProductValidationResult with validity and error list.
        """
        errors: list[str] = []

        # Determine which fields are "filled"
        name_filled = bool(name and name.strip())
        quantity_filled = quantity != 0
        price_filled = price != 0

        # Count filled fields
        filled_count = sum([name_filled, quantity_filled, price_filled])

        if filled_count > 0 and filled_count < 3:
            # Some but not all fields are filled
            if not name_filled:
                errors.append("Nome do produto obrigatório quando outros campos estão preenchidos.")
            if not quantity_filled:
                errors.append("Quantidade do produto obrigatória quando outros campos estão preenchidos.")
            if not price_filled:
                errors.append("Preço do produto obrigatório quando outros campos estão preenchidos.")

        return ProductValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_order(
        self,
        order: OrderInput,
    ) -> ValidationResult:
        """
        Validate a single order.

        Rules:
        - Date must be in valid YYYY-MM-DD format.
        - Supplier must be non-empty.
        - All products must be valid.

        Args:
            order: OrderInput to validate.

        Returns:
            ValidationResult with validity and error list.
        """
        errors: list[str] = []

        # Validate date format
        if not order.date or not order.date.strip():
            errors.append("Data da ordem obrigatória.")
        else:
            converted = br_date_to_iso(order.date)
            if not converted:
                errors.append(f"Formato de data inválido: '{order.date}'. Use AAAA-MM-DD.")

        # Validate supplier
        if not order.supplier or not order.supplier.strip():
            errors.append("Fornecedor obrigatório.")

        # Validate products
        for i, product in enumerate(order.products):
            product_result = self.validate_product(product.name, product.quantity, product.price)
            if not product_result.valid:
                for err in product_result.errors:
                    errors.append(f"Produto {i + 1}: {err}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_expense(
        self,
        description: str,
        value: int,
    ) -> ValidationResult:
        """
        Validate a single expense.

        Rule: description and value must both be filled or both empty.

        Args:
            description: Expense description string.
            value: Expense value in cents.

        Returns:
            ValidationResult with validity and error list.
        """
        errors: list[str] = []

        desc_filled = bool(description and description.strip())
        value_filled = value != 0

        if desc_filled != value_filled:
            if desc_filled:
                errors.append("Valor da despesa obrigatório quando a descrição está preenchida.")
            else:
                errors.append("Descrição da despesa obrigatória quando o valor está preenchido.")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_orders(
        self,
        orders: List[OrderInput],
    ) -> ValidationResult:
        """
        Validate a list of orders.

        Args:
            orders: List of OrderInput to validate.

        Returns:
            ValidationResult with validity and combined error list.
        """
        all_errors: list[str] = []

        for i, order in enumerate(orders):
            order_result = self.validate_order(order)
            if not order_result.valid:
                for err in order_result.errors:
                    all_errors.append(f"Ordem {i + 1}: {err}")

        return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)

    def validate_expenses(
        self,
        expenses: List[ExpenseInput],
    ) -> ValidationResult:
        """
        Validate a list of expenses.

        Args:
            expenses: List of ExpenseInput to validate.

        Returns:
            ValidationResult with validity and combined error list.
        """
        all_errors: list[str] = []

        for i, expense in enumerate(expenses):
            expense_result = self.validate_expense(expense.description, expense.value)
            if not expense_result.valid:
                for err in expense_result.errors:
                    all_errors.append(f"Despesa {i + 1}: {err}")

        return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)
