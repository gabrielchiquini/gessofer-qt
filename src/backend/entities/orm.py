from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "ORDER"

    ID: Mapped[str] = mapped_column("ID", String, primary_key=True)
    DATE: Mapped[date] = mapped_column("DATE", Date)
    SUPPLIER: Mapped[str] = mapped_column("SUPPLIER", String)
    SUPPLIER_NORMALIZED: Mapped[str] = mapped_column("SUPPLIER_NORMALIZED", String)
    NFE_KEY: Mapped[Optional[str]] = mapped_column("NFE_KEY", String, nullable=True)
    FREIGHT: Mapped[int] = mapped_column("FREIGHT", Integer)
    UNLOADING: Mapped[int] = mapped_column("UNLOADING", Integer)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)

    # Relationship to Product (backref on Product)
    products: Mapped[List["Product"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "PRODUCT"

    ID: Mapped[str] = mapped_column("ID", String, primary_key=True)
    NAME: Mapped[str] = mapped_column("NAME", String)
    NAME_NORMALIZED: Mapped[str] = mapped_column("NAME_NORMALIZED", String)
    QUANTITY: Mapped[int] = mapped_column("QUANTITY", Integer)
    PRICE: Mapped[int] = mapped_column("PRICE", Integer)
    TOTAL_PRICE: Mapped[int] = mapped_column("TOTAL_PRICE", Integer)
    ORDER_ID: Mapped[str] = mapped_column("ORDER_ID", ForeignKey("ORDER.ID"))
    ITEM_ORDINAL: Mapped[Optional[int]] = mapped_column("ITEM_ORDINAL", Integer, nullable=True)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)

    # Back-reference to Order
    order: Mapped["Order"] = relationship(back_populates="products")


class Expense(Base):
    __tablename__ = "EXPENSE"

    ID: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    MONTH: Mapped[str] = mapped_column("MONTH", String)
    DESCRIPTION: Mapped[str] = mapped_column("DESCRIPTION", String)
    VALUE: Mapped[int] = mapped_column("VALUE", Integer)
    CREATED_AT: Mapped[datetime] = mapped_column("CREATED_AT", DateTime)
    UPDATED_AT: Mapped[datetime] = mapped_column("UPDATED_AT", DateTime)
