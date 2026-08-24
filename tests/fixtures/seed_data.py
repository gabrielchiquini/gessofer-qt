from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ExpenseSeed:
    month: str
    description: str
    value: int


@dataclass(frozen=True)
class ProductSeed:
    id: str
    name: str
    quantity: int
    price: int
    total: int
    ordinal: int


@dataclass(frozen=True)
class OrderSeed:
    id: str
    date: date
    supplier: str
    nfe_key: str
    freight: int
    unloading: int
    products: tuple[ProductSeed, ...]


EXPENSES_DATA: tuple[ExpenseSeed, ...] = (
    ExpenseSeed("2024-07", "Material de escritório", 15000),
    ExpenseSeed("2024-07", "Taxa bancária", 7500),
    ExpenseSeed("2024-07", "Limpeza", 150000),
    ExpenseSeed("2024-08", "Manutenção elétrica", 45000),
    ExpenseSeed("2024-08", "Água e esgoto", 12000),
)

ORDERS_DATA: tuple[OrderSeed, ...] = (
    OrderSeed(
        id="order-a",
        date=date(2024, 7, 10),
        supplier="Cimento Portland",
        nfe_key="45678901234567",
        freight=5000,
        unloading=1000,
        products=(
            ProductSeed("prod-a1", "Cimento CP-II 50kg", 1, 25000, 25000, 1),
            ProductSeed("prod-a2", "Cimento CP-II 1kg", 1, 500, 500, 2),
        ),
    ),
    OrderSeed(
        id="order-b",
        date=date(2024, 7, 15),
        supplier="Areia Premium LTDA",
        nfe_key="12345678901234",
        freight=3000,
        unloading=500,
        products=(
            ProductSeed("prod-b1", "Areia média", 2, 120000, 240000, 1),
        ),
    ),
    OrderSeed(
        id="order-c",
        date=date(2024, 8, 5),
        supplier="Cimento Portland",
        nfe_key="98765432109876",
        freight=4000,
        unloading=800,
        products=(
            ProductSeed("prod-c1", "Cimento CP-I 50kg", 1, 22000, 22000, 1),
        ),
    ),
    OrderSeed(
        id="order-d",
        date=date(2024, 8, 20),
        supplier="Tijolo & Cia",
        nfe_key="11223344556677",
        freight=6000,
        unloading=1200,
        products=(
            ProductSeed("prod-d1", "Tijolo cerâmico 8 furos", 20, 1200, 24000, 1),
        ),
    ),
    OrderSeed(
        id="order-e",
        date=date(2024, 7, 25),
        supplier="Cimento Portland",
        nfe_key="55667788990011",
        freight=2000,
        unloading=500,
        products=(
            ProductSeed("prod-e1", "Cal hidratada 20kg", 2, 8000, 16000, 1),
        ),
    ),
)
