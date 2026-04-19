from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.db.models import ExchangeRate


class RatesService:
    def __init__(self, db: Session):
        self.db = db

    def list_rates(
        self,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExchangeRate]:
        stmt: Select[tuple[ExchangeRate]] = select(ExchangeRate)
        if currency:
            stmt = stmt.where(ExchangeRate.currency == currency)
        if date_from:
            stmt = stmt.where(ExchangeRate.date >= date_from)
        if date_to:
            stmt = stmt.where(ExchangeRate.date <= date_to)

        stmt = stmt.order_by(desc(ExchangeRate.date)).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def latest_rate_for_currency(self, currency: str) -> ExchangeRate | None:
        stmt = (
            select(ExchangeRate)
            .where(ExchangeRate.currency == currency)
            .order_by(desc(ExchangeRate.date))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_currencies(self) -> list[dict[str, str | None]]:
        stmt = (
            select(ExchangeRate.currency)
            .group_by(ExchangeRate.currency)
            .order_by(ExchangeRate.currency.asc())
        )
        rows = self.db.execute(stmt).all()
        return [{"currency": row.currency, "currency_name": None} for row in rows]

    def dataset_metadata(self) -> dict[str, int | date | None]:
        total_records = int(
            self.db.scalar(select(func.count()).select_from(ExchangeRate)) or 0
        )
        min_date = self.db.scalar(select(func.min(ExchangeRate.date)))
        max_date = self.db.scalar(select(func.max(ExchangeRate.date)))
        number_of_currencies = int(
            self.db.scalar(select(func.count(func.distinct(ExchangeRate.currency))))
            or 0
        )

        expected_daily_records = 0
        if min_date and max_date and number_of_currencies > 0:
            day_span = (max_date - min_date).days + 1
            expected_daily_records = day_span * number_of_currencies

        missing_records = max(expected_daily_records - total_records, 0)
        return {
            "total_records": total_records,
            "min_date": min_date,
            "max_date": max_date,
            "number_of_currencies": number_of_currencies,
            "expected_daily_records": expected_daily_records,
            "missing_records": missing_records,
        }

    def upsert_source_rate(
        self,
        target_currency: str,
        for_date: date,
        rate: float,
        currency_name: str | None = None,
    ) -> ExchangeRate:
        _ = currency_name
        target_currency = target_currency.upper()

        existing = self.db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.currency == target_currency,
                ExchangeRate.date == for_date,
            )
        )
        if existing:
            existing.rate = Decimal(str(rate))
            self.db.commit()
            self.db.refresh(existing)
            return existing

        created = ExchangeRate(
            currency=target_currency,
            date=for_date,
            rate=Decimal(str(rate)),
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created

    def delete_source_rate(self, target_currency: str, for_date: date) -> bool:
        target_currency = target_currency.upper()
        existing = self.db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.currency == target_currency,
                ExchangeRate.date == for_date,
            )
        )
        if not existing:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def _latest_usd_rate_for_currency_on_or_before(
        self, currency: str, target_date: date
    ) -> ExchangeRate | None:
        if currency.upper() == "USD":
            return None
        stmt = (
            select(ExchangeRate)
            .where(ExchangeRate.currency == currency, ExchangeRate.date <= target_date)
            .order_by(desc(ExchangeRate.date))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def latest_converted_rate(
        self, target_currency: str, base_currency: str = "USD"
    ) -> dict[str, str | float | date | None | bool] | None:
        target_currency = target_currency.upper()
        base_currency = base_currency.upper()

        if target_currency == base_currency:
            return {
                "base_currency": base_currency,
                "target_currency": target_currency,
                "date": date.today(),
                "rate": 1.0,
                "target_currency_name": target_currency,
                "forward_filled": False,
            }

        latest_target_stmt = (
            select(ExchangeRate)
            .where(ExchangeRate.currency == target_currency)
            .order_by(desc(ExchangeRate.date))
            .limit(1)
        )
        latest_target = self.db.scalar(latest_target_stmt)
        if not latest_target:
            return None

        target_usd_rate = float(latest_target.rate)
        forward_filled = False
        if base_currency == "USD":
            converted = target_usd_rate
        else:
            latest_base = self._latest_usd_rate_for_currency_on_or_before(
                currency=base_currency,
                target_date=latest_target.date,
            )
            if not latest_base:
                return None
            converted = target_usd_rate / float(latest_base.rate)
            forward_filled = latest_base.date < latest_target.date

        return {
            "base_currency": base_currency,
            "target_currency": target_currency,
            "date": latest_target.date,
            "rate": converted,
            "target_currency_name": None,
            "forward_filled": forward_filled,
        }

    def historical_converted_rates(
        self,
        target_currency: str,
        base_currency: str,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, str | float | date | None | bool]]:
        target_currency = target_currency.upper()
        base_currency = base_currency.upper()
        min_date = self.db.scalar(select(func.min(ExchangeRate.date)))
        if not min_date:
            return []

        target_first_date = self.db.scalar(
            select(func.min(ExchangeRate.date)).where(
                ExchangeRate.currency == target_currency
            )
        )
        if not target_first_date:
            return []

        base_first_date: date | None
        if base_currency == "USD":
            base_first_date = min_date
        else:
            base_first_date = self.db.scalar(
                select(func.min(ExchangeRate.date)).where(
                    ExchangeRate.currency == base_currency
                )
            )
            if not base_first_date:
                return []

        effective_start = max(date_from, target_first_date, base_first_date)
        if effective_start > date_to:
            return []

        target_rows = list(
            self.db.scalars(
                select(ExchangeRate)
                .where(
                    ExchangeRate.currency == target_currency,
                    ExchangeRate.date <= date_to,
                )
                .order_by(ExchangeRate.date.asc())
            ).all()
        )
        if not target_rows:
            return []

        base_rows: list[ExchangeRate] = []
        if base_currency != "USD":
            base_rows = list(
                self.db.scalars(
                    select(ExchangeRate)
                    .where(
                        ExchangeRate.currency == base_currency,
                        ExchangeRate.date <= date_to,
                    )
                    .order_by(ExchangeRate.date.asc())
                ).all()
            )
            if not base_rows:
                return []

        items: list[dict[str, str | float | date | None | bool]] = []
        current_date = effective_start
        end_date = date_to

        target_idx = 0
        current_target = target_rows[0]
        while (
            target_idx + 1 < len(target_rows)
            and target_rows[target_idx + 1].date <= effective_start
        ):
            target_idx += 1
            current_target = target_rows[target_idx]

        base_idx = 0
        current_base = base_rows[0] if base_rows else None
        if base_currency != "USD":
            while (
                base_idx + 1 < len(base_rows)
                and base_rows[base_idx + 1].date <= effective_start
            ):
                base_idx += 1
                current_base = base_rows[base_idx]

        while current_date <= end_date:
            while (
                target_idx + 1 < len(target_rows)
                and target_rows[target_idx + 1].date <= current_date
            ):
                target_idx += 1
                current_target = target_rows[target_idx]

            if current_target.date > current_date:
                current_date += timedelta(days=1)
                continue

            if base_currency == "USD":
                converted = float(current_target.rate)
                forward_filled = current_target.date < current_date
            else:
                while (
                    base_idx + 1 < len(base_rows)
                    and base_rows[base_idx + 1].date <= current_date
                ):
                    base_idx += 1
                    current_base = base_rows[base_idx]

                if current_base is None or current_base.date > current_date:
                    current_date += timedelta(days=1)
                    continue

                converted = float(current_target.rate) / float(current_base.rate)
                forward_filled = (
                    current_target.date < current_date
                    or current_base.date < current_date
                )

            items.append(
                {
                    "base_currency": base_currency,
                    "target_currency": target_currency,
                    "date": current_date,
                    "rate": converted,
                    "target_currency_name": None,
                    "forward_filled": forward_filled,
                }
            )
            current_date += timedelta(days=1)

        return items
