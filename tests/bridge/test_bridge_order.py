"""Unit tests for OrderBridge.delete_order()."""

from __future__ import annotations

from typing import Callable

import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

from bridge.order import OrderBridge
from backend.repositories.order_repository import OrderRepository


class TestOrderBridgeDeleteSuccess:
    """TC-21: Bridge delete_order — Success."""

    def test_delete_order_success(
        self,
        session_factory: Callable[[], Session],
    ) -> None:
        save_handler: MagicMock = MagicMock()
        bridge: OrderBridge = OrderBridge(save_handler, session_factory)

        call_log: list[str] = []

        def log_products(*args: object, **kwargs: object) -> None:
            call_log.append("delete_order_products")

        def log_orders(*args: object, **kwargs: object) -> None:
            call_log.append("delete_orders")

        with patch.object(
            OrderRepository, "delete_order_products", side_effect=log_products
        ), patch.object(
            OrderRepository, "delete_orders", side_effect=log_orders
        ):

            result: bool = bridge.delete_order("test-order-uuid")

            assert result is True

            # Verify both methods were called exactly once
            assert call_log.count("delete_order_products") == 1
            assert call_log.count("delete_orders") == 1

            # Verify call order: products must be deleted before orders
            products_idx: int = call_log.index("delete_order_products")
            orders_idx: int = call_log.index("delete_orders")
            assert products_idx < orders_idx


class TestOrderBridgeDeleteFailure:
    """TC-22: Bridge delete_order — Failure."""

    def test_delete_order_failure_returns_false(
        self,
        session_factory: Callable[[], Session],
    ) -> None:
        save_handler: MagicMock = MagicMock()
        bridge: OrderBridge = OrderBridge(save_handler, session_factory)

        with patch.object(
            OrderRepository, "delete_order_products",
            side_effect=Exception("DB error"),
        ) as mock_delete_products, patch.object(
            OrderRepository, "delete_orders"
        ) as mock_delete_orders:

            result: bool = bridge.delete_order("test-order-uuid")

            assert result is False

            # Verify delete_orders was NOT called (products delete failed first)
            mock_delete_orders.assert_not_called()
