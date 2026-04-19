import os
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExchangeRate(Base):
    __tablename__ = "currency_rates"
    __table_args__ = (
        Index("ix_currency_rates_currency_date", "currency", "date"),
        {"schema": f"src_{os.getenv('TARGET', 'dev')}"},
    )

    currency: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
