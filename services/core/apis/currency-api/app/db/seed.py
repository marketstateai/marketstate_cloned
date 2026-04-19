import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ExchangeRate


def seed_exchange_rates_if_empty(db: Session, seed_data_path: str) -> int:
    existing_count = db.scalar(select(func.count()).select_from(ExchangeRate))
    if existing_count and existing_count > 0:
        return 0

    seed_path = Path(seed_data_path)
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {seed_path}")

    raw_rows = json.loads(seed_path.read_text(encoding="utf-8"))
    rows = [
        ExchangeRate(
            currency=row["currency"],
            date=date.fromisoformat(row["date"]),
            rate=Decimal(row["rate"]),
        )
        for row in raw_rows
    ]

    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)
