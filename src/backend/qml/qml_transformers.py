from __future__ import annotations

from typing import Any

from backend.entities.orm import Expense, Order, Product
from backend.models.dto import OrderInput, PageResponse
from backend.services.freight_distribution import FreightDistributionResult
from backend.services.xml_import_service import XmlImportResult


def orm_order_to_dict(order: Order) -> dict[str, Any]:
    """Transform an ORM Order entity into a QML-compatible dict."""
    return {
        "id": order.ID,
        "date": order.DATE.isoformat() if order.DATE else "",
        "supplier": order.SUPPLIER,
        "nfeKey": order.NFE_KEY or "",
        "freight": order.FREIGHT,
        "unloading": order.UNLOADING,
        "products": [orm_product_to_dict(p) for p in order.products],
    }


def orm_product_to_dict(product: Product) -> dict[str, Any]:
    """Transform an ORM Product entity into a QML-compatible dict."""
    return {
        "id": product.ID,
        "name": product.NAME,
        "quantity": product.QUANTITY,
        "price": product.PRICE,
        "total": product.TOTAL_PRICE,
        "order_id": product.ORDER_ID,
        "itemOrdinal": product.ITEM_ORDINAL,
    }


def dict_to_order_input(d: dict[str, Any]) -> OrderInput:
    """Transform a QML dict (from save/distribute/validate) into an OrderInput DTO."""
    products: list[OrderInput] = []
    for p in d.get("products", []):
        pi = OrderInput(
            id=p.get("id", ""),
            date="",
            supplier="",
            nfe_key="",
            freight=0,
            unloading=0,
            products=[],
        )
        pi.name = p.get("name", "")
        pi.quantity = p.get("quantity", 0)
        pi.price = p.get("price", 0)
        pi.total = p.get("total", 0)
        pi.order_id = p.get("order_id", "")
        pi.item_ordinal = p.get("itemOrdinal")
        products.append(pi)
    return OrderInput(
        id=d.get("id", ""),
        date=d.get("date", ""),
        supplier=d.get("supplier", ""),
        nfe_key=d.get("nfeKey", ""),
        freight=d.get("freight", 0),
        unloading=d.get("unloading", 0),
        products=products,
    )


def expense_to_dict(expense: Expense) -> dict[str, Any]:
    """Transform an ORM Expense entity into a QML-compatible dict."""
    return {
        "id": expense.ID,
        "month": expense.MONTH,
        "description": expense.DESCRIPTION,
        "value": expense.VALUE,
    }


def product_page_to_dict(response: PageResponse[Product]) -> dict[str, Any]:
    """Transform a PageResponse[Product] into a QML-compatible dict."""
    return {
        "items": [orm_product_to_dict(p) for p in response.items],
        "page": response.page,
        "page_count": response.page_count,
        "total": response.total,
        "page_size": response.page_size,
    }


def freight_result_to_dict(result: FreightDistributionResult) -> dict[str, Any]:
    """Transform a FreightDistributionResult into a QML-compatible dict."""
    return {
        "order_id": result.order_id,
        "old_freight": result.old_freight,
        "old_unloading": result.old_unloading,
        "ratio": result.ratio,
        "products_total_before": result.products_total_before,
        "products_total_after": result.products_total_after,
        "new_products": [
            {
                "id": p.id,
                "name": p.name,
                "quantity": p.quantity,
                "price": p.price,
                "total": p.total,
                "order_id": p.order_id,
                "itemOrdinal": p.item_ordinal,
            }
            for p in result.new_products
        ],
    }


def xml_import_result_to_dict(result: XmlImportResult) -> dict[str, Any]:
    """Transform an XmlImportResult into a QML-compatible dict."""
    return {
        "orders": [
            {
                "id": o.id,
                "date": o.date,
                "supplier": o.supplier,
                "nfeKey": o.nfe_key,
                "freight": o.freight,
                "unloading": o.unloading,
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "quantity": p.quantity,
                        "price": p.price,
                        "total": p.total,
                        "order_id": p.order_id,
                        "itemOrdinal": p.item_ordinal,
                    }
                    for p in o.products
                ],
            }
            for o in result.orders
        ],
        "warnings": result.warnings,
    }
