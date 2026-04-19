import os
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _table_args():
    idx = Index("ix_currency_rates_currency_date", "currency", "date")
    # Optional explicit schema for Postgres deployments.
    # Leave unset for SQLite/dev/tests.
    schema = os.getenv("DB_SCHEMA", "").strip()
    if not schema:
        return (idx,)
    return (idx, {"schema": schema})


class ExchangeRate(Base):
    __tablename__ = "currency_rates"
    __table_args__ = _table_args()

    currency: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
