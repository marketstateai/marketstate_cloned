from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.rates import router as rates_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.seed import seed_exchange_rates_if_empty
from app.db.session import SessionLocal, init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_exchange_rates_if_empty(db=db, seed_data_path=settings.seed_data_path)
        finally:
            db.close()
    yield


tags_metadata = [
    {
        "name": "rates",
        "description": "Latest and historical currency conversion endpoints.",
    },
    {
        "name": "currencies",
        "description": "Currency catalogue and dataset metadata.",
    },
]

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    summary="USD-baseline currency conversion API",
    description=(
        "This API provides latest and historical currency conversion results from a "
        "USD-baseline dataset. All endpoints require an API token via the `x-api-token` header."
    ),
    contact={
        "name": "Currency API Team",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.parsed_allowed_hosts)

if settings.parsed_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )

app.include_router(rates_router, prefix=settings.api_prefix)
