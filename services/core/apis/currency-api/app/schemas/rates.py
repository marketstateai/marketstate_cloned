from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    date: date_type
    rate: float


class ExchangeRateQueryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    count: int
    items: list[ExchangeRateRead]


class CurrencyRead(BaseModel):
    currency: str = Field(description="Currency code, e.g. USD, EUR, AAVE.")
    currency_name: str | None = Field(
        default=None,
        description="Human-readable currency name when available.",
    )


class DatasetMetadata(BaseModel):
    total_records: int = Field(description="Total number of rows in the dataset.")
    min_date: date_type | None = Field(description="Earliest date present in the dataset.")
    max_date: date_type | None = Field(description="Latest date present in the dataset.")
    number_of_currencies: int = Field(description="Count of distinct currencies.")
    expected_daily_records: int = Field(
        description="Expected rows for full daily coverage across all currencies.",
    )
    missing_records: int = Field(
        description="Estimated number of missing daily rows in the dataset.",
    )


class CurrencyQueryResult(BaseModel):
    count: int = Field(description="Number of currencies returned.")
    items: list[CurrencyRead] = Field(description="Currency list.")
    metadata: DatasetMetadata = Field(description="Dataset summary statistics.")


class ConvertedRateRead(BaseModel):
    base_currency: str = Field(description="Base currency code.")
    target_currency: str = Field(description="Target currency code.")
    date: date_type = Field(description="Date for this converted rate point.")
    rate: float = Field(description="Converted rate from base to target.")
    target_currency_name: str | None = Field(
        default=None,
        description="Human-readable target currency name when available.",
    )
    forward_filled: bool = Field(
        description="True when the value was forward-filled from prior available data.",
    )


class ConvertedRateQueryResult(BaseModel):
    count: int = Field(description="Number of converted points returned.")
    items: list[ConvertedRateRead] = Field(description="Converted rate series.")


class HistoricalRatesRequest(BaseModel):
    target_currency: str = Field(description="Target currency code, e.g. EUR.")
    base_currency: str = Field(default="USD", description="Base currency code.")
    date_from: date_type = Field(description="Range start date in YYYY-MM-DD.")
    date_to: date_type = Field(description="Range end date in YYYY-MM-DD.")


class SourceRateUpsertRequest(BaseModel):
    target_currency: str = Field(description="Target currency code to store, e.g. EUR.")
    date: date_type = Field(description="Record date in YYYY-MM-DD.")
    rate: float = Field(description="Rate of target currency expressed against USD baseline.")
    currency_name: str | None = Field(
        default=None,
        description="Optional human-readable currency name.",
    )


class DeleteResult(BaseModel):
    deleted: bool = Field(description="True if a source record was deleted.")
