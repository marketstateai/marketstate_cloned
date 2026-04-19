from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import require_api_token
from app.db.session import get_db
from app.schemas.rates import (
    ConvertedRateQueryResult,
    ConvertedRateRead,
    DeleteResult,
    CurrencyRead,
    CurrencyQueryResult,
    HistoricalRatesRequest,
    SourceRateUpsertRequest,
    ExchangeRateRead,
)
from app.services.rates_service import RatesService

router = APIRouter(dependencies=[Depends(require_api_token)])


def get_rates_service(db: Session = Depends(get_db)) -> RatesService:
    return RatesService(db=db)


@router.get(
    "/rates/latest",
    response_model=ConvertedRateRead,
    tags=["rates"],
    summary="Get Latest Conversion Rate",
    description=(
        "Returns the most recent conversion rate from `base_currency` to `target_currency`."
    ),
    response_description="Latest available converted rate.",
)
def latest_converted_rate(
    target_currency: str = Query(..., description="Target currency code, e.g. EUR."),
    base_currency: str = Query("USD", description="Base currency code, default is USD."),
    service: RatesService = Depends(get_rates_service),
):
    item = service.latest_converted_rate(
        target_currency=target_currency,
        base_currency=base_currency,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Currency pair not found")
    return ConvertedRateRead.model_validate(item)


@router.get(
    "/rates/historical",
    response_model=ConvertedRateQueryResult,
    tags=["rates"],
    summary="Get Historical Conversion Series (GET)",
    description=(
        "Returns continuous daily conversion rates for the requested date range, "
        "including forward-filled rows where source dates are missing."
    ),
    response_description="Historical converted rate series.",
)
def historical_converted_rates(
    target_currency: str = Query(..., description="Target currency code, e.g. EUR."),
    base_currency: str = Query("USD", description="Base currency code, default is USD."),
    date_from: date = Query(..., description="Range start date in YYYY-MM-DD."),
    date_to: date = Query(..., description="Range end date in YYYY-MM-DD."),
    service: RatesService = Depends(get_rates_service),
):
    return _build_historical_response(
        target_currency=target_currency,
        base_currency=base_currency,
        date_from=date_from,
        date_to=date_to,
        service=service,
    )


@router.post(
    "/rates/historical",
    response_model=ConvertedRateQueryResult,
    tags=["rates"],
    summary="Get Historical Conversion Series (POST)",
    description="Same as GET `/rates/historical`, using JSON request body input.",
    response_description="Historical converted rate series.",
)
def historical_converted_rates_post(
    payload: HistoricalRatesRequest,
    service: RatesService = Depends(get_rates_service),
):
    return _build_historical_response(
        target_currency=payload.target_currency,
        base_currency=payload.base_currency,
        date_from=payload.date_from,
        date_to=payload.date_to,
        service=service,
    )


@router.put(
    "/rates/historical",
    response_model=ConvertedRateQueryResult,
    tags=["rates"],
    summary="Get Historical Conversion Series (PUT)",
    description="Same as GET `/rates/historical`, using JSON request body input.",
    response_description="Historical converted rate series.",
)
def historical_converted_rates_put(
    payload: HistoricalRatesRequest,
    service: RatesService = Depends(get_rates_service),
):
    return _build_historical_response(
        target_currency=payload.target_currency,
        base_currency=payload.base_currency,
        date_from=payload.date_from,
        date_to=payload.date_to,
        service=service,
    )


def _build_historical_response(
    target_currency: str,
    base_currency: str,
    date_from: date,
    date_to: date,
    service: RatesService,
) -> ConvertedRateQueryResult:
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")
    items = service.historical_converted_rates(
        target_currency=target_currency,
        base_currency=base_currency,
        date_from=date_from,
        date_to=date_to,
    )
    normalized = [ConvertedRateRead.model_validate(item) for item in items]
    return ConvertedRateQueryResult(count=len(normalized), items=normalized)


@router.get(
    "/currencies",
    response_model=CurrencyQueryResult,
    tags=["currencies"],
    summary="List Available Currencies",
    description=(
        "Returns unique currencies found in the dataset plus summary metadata "
        "(record counts, date bounds, and missing-record estimate)."
    ),
    response_description="Currency list and dataset metadata.",
)
def list_currencies(service: RatesService = Depends(get_rates_service)):
    items = service.list_currencies()
    metadata = service.dataset_metadata()
    normalized = [CurrencyRead.model_validate(item) for item in items]
    return CurrencyQueryResult(
        count=len(normalized),
        items=normalized,
        metadata=metadata,
    )


@router.put(
    "/rates/source-record",
    response_model=ExchangeRateRead,
    tags=["rates"],
    summary="Upsert Source Rate Record",
    description=(
        "Creates or updates a raw USD-baseline source record for a specific "
        "target currency and date."
    ),
)
def upsert_source_record(
    payload: SourceRateUpsertRequest,
    service: RatesService = Depends(get_rates_service),
):
    row = service.upsert_source_rate(
        target_currency=payload.target_currency,
        for_date=payload.date,
        rate=payload.rate,
        currency_name=payload.currency_name,
    )
    return ExchangeRateRead.model_validate(row)


@router.delete(
    "/rates/source-record",
    response_model=DeleteResult,
    tags=["rates"],
    summary="Delete Source Rate Record",
    description="Deletes a raw USD-baseline source record by target currency and date.",
)
def delete_source_record(
    target_currency: str = Query(..., description="Target currency code, e.g. EUR."),
    date: date = Query(..., description="Record date in YYYY-MM-DD."),
    service: RatesService = Depends(get_rates_service),
):
    deleted = service.delete_source_rate(
        target_currency=target_currency,
        for_date=date,
    )
    return DeleteResult(deleted=deleted)
