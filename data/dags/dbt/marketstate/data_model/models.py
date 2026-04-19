from __future__ import annotations

"""
Snowflake-style financial data model (core only).

Design goals:
- Center on *daily* stock observations (prices + a few daily-changing attributes).
- Keep dimensions stable and extensible (exchange/country/currency, company, listing).
- Support financial modeling via periodic financial statements (income/balance/cashflow).

This file is used to generate an ERD via `generate_erd_html.py` (SQLite introspection),
so it emphasizes PK/FK relationships and clear table naming over warehouse-specific DDL.
"""

from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

SK_LEN = 32  # stable surrogate key (e.g., hex md5)


# -------------------------
# Core conformed dimensions
# -------------------------


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key = Column(Integer, primary_key=True)  # yyyymmdd
    date = Column(Date, nullable=False, unique=True)
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    quarter = Column(Integer, nullable=True)
    day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)


class DimCurrency(Base):
    __tablename__ = "dim_currency"

    currency_code = Column(String(16), primary_key=True)  # ISO-4217
    currency_name = Column(String(128), nullable=True)


class DimCountry(Base):
    __tablename__ = "dim_country"

    alpha2_code = Column(String(2), primary_key=True)  # ISO-3166-1 alpha-2
    english_short_name = Column(String(128), nullable=True)
    french_short_name = Column(String(128), nullable=True)
    alpha3_code = Column(String(3), nullable=True)
    numeric_code = Column(String(8), nullable=True)
    country_name = Column(String(128), nullable=True)
    iso3166_2 = Column(String(16), nullable=True)
    region = Column(String(128), nullable=True)
    sub_region = Column(String(128), nullable=True)
    intermediate_region = Column(String(128), nullable=True)
    region_code = Column(String(16), nullable=True)
    sub_region_code = Column(String(16), nullable=True)
    intermediate_region_code = Column(String(16), nullable=True)


class DimExchange(Base):
    __tablename__ = "dim_exchange"

    exchange_sk = Column(String(SK_LEN), primary_key=True)
    exchange_name = Column(String(255), nullable=True)
    country = Column(String(128), nullable=True)
    market_identifier_code = Column(
        String(32),
        ForeignKey("dim_market_identifier_code.mic"),
        nullable=False,
        unique=True,
    )
    currency = Column(String(16), ForeignKey("dim_currency.currency_code"), nullable=True)
    stock_count = Column(Integer, nullable=True)
    url = Column(String(2048), nullable=True)
    capture_date = Column(String(32), nullable=True)
    exchange_abbreviation = Column(String(64), nullable=True)
    exchange_name_local_language = Column(String(255), nullable=True)
    trade_accessibility = Column(String(128), nullable=True)
    yahoo_suffix = Column(String(32), nullable=True)

    currency_ref = relationship("DimCurrency")
    mic_ref = relationship("DimMarketIdentifierCode")


class DimMarketIdentifierCode(Base):
    __tablename__ = "dim_market_identifier_code"

    mic = Column(String(16), primary_key=True)
    operating_mic = Column(String(16), nullable=True)
    oprt_sgmt = Column(String(32), nullable=True)
    market_name_institution_description = Column(String(255), nullable=True)
    legal_entity_name = Column(String(255), nullable=True)
    lei = Column(String(32), nullable=True)
    market_category_code = Column(String(16), nullable=True)
    acronym = Column(String(64), nullable=True)
    iso_country_code_iso3166 = Column(String(8), nullable=True)
    city = Column(String(128), nullable=True)
    website = Column(String(2048), nullable=True)
    status = Column(String(32), nullable=True)
    creation_date = Column(Integer, nullable=True)
    last_update_date = Column(Integer, nullable=True)
    last_validation_date = Column(Float, nullable=True)
    expiry_date = Column(Float, nullable=True)
    comments = Column(String(4096), nullable=True)


class DimCompany(Base):
    __tablename__ = "dim_company"

    company_sk = Column(String(SK_LEN), primary_key=True)
    company_name = Column(String(255), nullable=False, unique=True)
    website = Column(String(2048), nullable=True)
    phone = Column(String(64), nullable=True)
    address1 = Column(String(255), nullable=True)
    address2 = Column(String(255), nullable=True)
    city = Column(String(128), nullable=True)
    zip = Column(String(32), nullable=True)
    country_of_origin = Column(String(128), nullable=True)
    financial_currency = Column(String(16), nullable=True)
    sector = Column(String(128), nullable=True)
    industry = Column(String(128), nullable=True)
    primary_market = Column(String(128), nullable=True)
    market_share = Column(String(128), nullable=True)
    wikipedia_url = Column(String(2048), nullable=True)
    business_summary = Column(String(4096), nullable=True)
    main_market_segments = Column(String(4096), nullable=True)
    geo_markets = Column(String(4096), nullable=True)
    products = Column(String(4096), nullable=True)
    business_summary_int = Column(String(8192), nullable=True)


class DimSymbol(Base):
    __tablename__ = "dim_symbol"

    symbol_sk = Column(String(SK_LEN), primary_key=True)
    yf_symbol = Column(String(64), nullable=False, unique=True)

    company_sk = Column(String(SK_LEN), ForeignKey("dim_company.company_sk"), nullable=True)

    company = relationship("DimCompany")
    isin = Column(String(32), nullable=True)
    cusip = Column(String(16), nullable=True)
    # Most analyses should anchor on the primary listing (but additional listings still exist in dim_listing).
    primary_listing_sk = Column(String(SK_LEN), ForeignKey("dim_listing.listing_sk"), nullable=True)
    primary_listing = relationship("DimListing", foreign_keys=[primary_listing_sk])


class DimListing(Base):
    """
One row per symbol listed on an exchange.

`exchange_symbol` is the exchange-specific identifier used for time-series inputs.
"""

    __tablename__ = "dim_listing"

    listing_sk = Column(String(SK_LEN), primary_key=True)
    exchange_symbol = Column(String(64), nullable=False)

    symbol_sk = Column(String(SK_LEN), ForeignKey("dim_symbol.symbol_sk"), nullable=False)
    exchange_sk = Column(String(SK_LEN), ForeignKey("dim_exchange.exchange_sk"), nullable=False)

    symbol = relationship("DimSymbol")
    exchange = relationship("DimExchange")

    __table_args__ = (
        UniqueConstraint("symbol_sk", "exchange_sk", name="uq_dim_listing_symbol_exchange"),
        UniqueConstraint("exchange_sk", "exchange_symbol", name="uq_dim_listing_exchange_symbol"),
    )
    primary_symbol = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=True)
    is_primary = Column(Boolean, nullable=True)


class FactIpo(Base):
    """
IPO / first listing event (first pass).

This anchors the lifecycle:
company exists + exchange exists -> IPO event -> primary listing (+ optional secondary listings).
"""

    __tablename__ = "fact_ipo"

    company_sk = Column(String(SK_LEN), ForeignKey("dim_company.company_sk"), primary_key=True)
    listing_sk = Column(String(SK_LEN), ForeignKey("dim_listing.listing_sk"), primary_key=True)

    ipo_date_key = Column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    ipo_exchange_sk = Column(String(SK_LEN), ForeignKey("dim_exchange.exchange_sk"), nullable=True)

    ipo_price = Column(Float, nullable=True)
    ipo_currency_code = Column(String(16), ForeignKey("dim_currency.currency_code"), nullable=True)

    company = relationship("DimCompany")
    listing = relationship("DimListing")
    ipo_date = relationship("DimDate")
    ipo_exchange = relationship("DimExchange")
    ipo_currency = relationship("DimCurrency")

    __table_args__ = (
        UniqueConstraint("listing_sk", name="uq_fact_ipo_listing"),
    )


class Stocks(Base):
    __tablename__ = "stocks"

    stg_stocks_sk = Column(String(SK_LEN), primary_key=True)
    exchange_symbol = Column(String(64), ForeignKey("dim_listing.exchange_symbol"), nullable=True)
    capture_date = Column(Date, nullable=True)
    yf_symbol = Column(String(64), ForeignKey("dim_symbol.yf_symbol"), nullable=True)

    company_name = Column(String(255), nullable=True)
    address = Column(String(512), nullable=True)
    company_country = Column(String(128), nullable=True)
    website = Column(String(2048), nullable=True)
    company_officers = Column(Text, nullable=True)
    sector = Column(String(128), nullable=True)
    industry = Column(String(128), nullable=True)
    long_business_summary = Column(Text, nullable=True)

    exchange = Column(String(255), nullable=True)
    company_currency = Column(String(16), ForeignKey("dim_currency.currency_code"), nullable=True)
    exchange_currency = Column(String(16), ForeignKey("dim_currency.currency_code"), nullable=True)

    five_year_avg_dividend_yield = Column(String(64), nullable=True)
    full_time_employees = Column(Integer, nullable=True)
    shares_outstanding = Column(Integer, nullable=True)
    last_dividend_value = Column(Float, nullable=True)
    last_dividend_date = Column(Date, nullable=True)
    last_fiscal_year_end_date = Column(Date, nullable=True)
    first_trade_date = Column(Date, nullable=True)
    market_identifier_code = Column(
        String(32),
        ForeignKey("dim_exchange.market_identifier_code"),
        nullable=True,
    )

    listing = relationship("DimListing", foreign_keys=[exchange_symbol])
    symbol = relationship("DimSymbol", foreign_keys=[yf_symbol])
    company_currency_ref = relationship("DimCurrency", foreign_keys=[company_currency])
    exchange_currency_ref = relationship("DimCurrency", foreign_keys=[exchange_currency])
    exchange_ref = relationship("DimExchange", foreign_keys=[market_identifier_code])


# -------------------------
# Classification (snowflake)
# -------------------------


class DimGicsSector(Base):
    __tablename__ = "dim_gics_sector"

    sector_code = Column(Integer, primary_key=True)
    sector = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)


class DimGicsIndustry(Base):
    __tablename__ = "dim_gics_industry"

    industry_code = Column(Integer, primary_key=True)
    industry = Column(String(128), nullable=True)
    sector_code = Column(Integer, ForeignKey("dim_gics_sector.sector_code"), nullable=True)

    sector = relationship("DimGicsSector")
    description = Column(Text, nullable=True)


class DimGicsSubIndustry(Base):
    __tablename__ = "dim_gics_sub_industry"

    sub_industry_code = Column(Integer, primary_key=True)
    sub_industry = Column(String(128), nullable=True)
    industry_code = Column(Integer, ForeignKey("dim_gics_industry.industry_code"), nullable=True)

    industry = relationship("DimGicsIndustry")
    description = Column(Text, nullable=True)


#
# NOTE: `bridge_company_gics` removed per request.
# If/when you want time-variant classifications again, reintroduce it as an effective-dated bridge.


# -------------------------
# Daily facts (center)
# -------------------------


class FactFxRateDaily(Base):
    __tablename__ = "fact_fx_rate_daily"

    date_key = Column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    from_currency_code = Column(
        String(16),
        ForeignKey("dim_currency.currency_code"),
        primary_key=True,
    )
    to_currency_code = Column(
        String(16),
        ForeignKey("dim_currency.currency_code"),
        primary_key=True,
    )

    rate = Column(Float, nullable=False)

    date = relationship("DimDate")
    from_currency = relationship("DimCurrency", foreign_keys=[from_currency_code])
    to_currency = relationship("DimCurrency", foreign_keys=[to_currency_code])
    provider = Column(String(64), nullable=True)
    is_estimated = Column(Boolean, nullable=True)


class FactStockDaily(Base):
    """
One row per listing per day.

Core time-series measures + a small set of daily-changing attributes.
"""

    __tablename__ = "fact_stock_daily"

    date_key = Column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    listing_sk = Column(String(SK_LEN), ForeignKey("dim_listing.listing_sk"), primary_key=True)

    # prices (keep minimal; add OHLC/adj_close later)
    close_price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)

    # daily-changing attributes (often sparse / vendor-driven)
    market_cap = Column(Float, nullable=True)
    shares_outstanding = Column(Float, nullable=True)

    # currency context for the observation (typically listing currency)
    currency_code = Column(String(16), ForeignKey("dim_currency.currency_code"), nullable=True)

    date = relationship("DimDate")
    listing = relationship("DimListing")
    currency = relationship("DimCurrency")
    open_price = Column(Float, nullable=True)
    adj_close_price = Column(Float, nullable=True)


# -------------------------
# Financial modeling layer
# -------------------------


class DimFinancialPeriod(Base):
    __tablename__ = "dim_financial_period"

    period_sk = Column(String(SK_LEN), primary_key=True)
    country_code = Column(String(2), ForeignKey("dim_country.alpha2_code"), nullable=True)
    period_type = Column(String(16), nullable=False)  # annual|quarterly|ttm

    period_end_date = Column(Date, nullable=False)
    period_end_date_key = Column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    fiscal_year = Column(Integer, nullable=True)
    fiscal_quarter = Column(Integer, nullable=True)  # 1-4

    period_end = relationship("DimDate")
    country = relationship("DimCountry")

    __table_args__ = (
        UniqueConstraint(
            "country_code",
            "period_type",
            "period_end_date_key",
            name="uq_dim_financial_period_type_end",
        ),
    )
    period_label = Column(String(32), nullable=True)
    is_audited = Column(Boolean, nullable=True)


class FactIncomeStatement(Base):
    __tablename__ = "fact_income_statement"

    company_sk = Column(String(SK_LEN), ForeignKey("dim_company.company_sk"), primary_key=True)
    period_sk = Column(String(SK_LEN), ForeignKey("dim_financial_period.period_sk"), primary_key=True)
    currency_code = Column(String(16), ForeignKey("dim_currency.currency_code"), primary_key=True)

    total_revenue = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)

    company = relationship("DimCompany")
    period = relationship("DimFinancialPeriod")
    currency = relationship("DimCurrency")
    cost_of_revenue = Column(Float, nullable=True)
    shares_diluted = Column(Float, nullable=True)


class FactBalanceSheet(Base):
    __tablename__ = "fact_balance_sheet"

    company_sk = Column(String(SK_LEN), ForeignKey("dim_company.company_sk"), primary_key=True)
    period_sk = Column(String(SK_LEN), ForeignKey("dim_financial_period.period_sk"), primary_key=True)
    currency_code = Column(String(16), ForeignKey("dim_currency.currency_code"), primary_key=True)

    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)

    company = relationship("DimCompany")
    period = relationship("DimFinancialPeriod")
    currency = relationship("DimCurrency")
    current_assets = Column(Float, nullable=True)
    current_liabilities = Column(Float, nullable=True)


class FactCashFlow(Base):
    __tablename__ = "fact_cash_flow"

    company_sk = Column(String(SK_LEN), ForeignKey("dim_company.company_sk"), primary_key=True)
    period_sk = Column(String(SK_LEN), ForeignKey("dim_financial_period.period_sk"), primary_key=True)
    currency_code = Column(String(16), ForeignKey("dim_currency.currency_code"), primary_key=True)

    operating_cash_flow = Column(Float, nullable=True)
    capital_expenditures = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)

    company = relationship("DimCompany")
    period = relationship("DimFinancialPeriod")
    currency = relationship("DimCurrency")
    dividends_paid = Column(Float, nullable=True)
    share_buybacks = Column(Float, nullable=True)


# -------------------------
# Reporting layer (derived)
# -------------------------


class RptStockDaily(Base):
    """
Denormalized daily time-series report for interactive filtering.

Primary use: "one big table" with price series + country/exchange/industry filters.
"""

    __tablename__ = "rpt_stock_daily"

    date_key = Column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    listing_sk = Column(String(SK_LEN), ForeignKey("dim_listing.listing_sk"), primary_key=True)

    # Measures (from fact_stock_daily)
    close_price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    market_cap = Column(Float, nullable=True)

    # Filter attributes (denormalized for convenience)
    exchange_sk = Column(String(SK_LEN), ForeignKey("dim_exchange.exchange_sk"), nullable=True)
    country_code = Column(String(2), ForeignKey("dim_country.alpha2_code"), nullable=True)
    industry_code = Column(Integer, ForeignKey("dim_gics_industry.industry_code"), nullable=True)

    date = relationship("DimDate")
    listing = relationship("DimListing")
    exchange = relationship("DimExchange")
    country = relationship("DimCountry")
    industry = relationship("DimGicsIndustry")
    exchange_symbol = Column(String(64), nullable=True)
    yf_symbol = Column(String(64), nullable=True)


class RptGlobalMarketValuationDaily(Base):
    """
Global "market dashboard" report (daily) for cross-sectional valuation/size views.

Example uses:
- total market cap by country/sector/industry
- implied valuation aggregates (P/E, P/S) using latest available financials
"""

    __tablename__ = "rpt_global_market_valuation_daily"

    date_key = Column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    country_code = Column(String(2), ForeignKey("dim_country.alpha2_code"), primary_key=True)
    sector_code = Column(Integer, ForeignKey("dim_gics_sector.sector_code"), primary_key=True)

    listing_count = Column(Integer, nullable=True)
    total_market_cap_usd = Column(Float, nullable=True)

    total_revenue_ttm_usd = Column(Float, nullable=True)
    total_net_income_ttm_usd = Column(Float, nullable=True)

    # Simple aggregate valuation metrics (derived)
    pe = Column(Float, nullable=True)  # total_market_cap / total_net_income
    ps = Column(Float, nullable=True)  # total_market_cap / total_revenue

    date = relationship("DimDate")
    country = relationship("DimCountry")
    sector = relationship("DimGicsSector")
    total_gross_profit_ttm_usd = Column(Float, nullable=True)
    data_version = Column(String(32), nullable=True)


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parent / "mini.db"
    if db_path.exists():
        db_path.unlink()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    Base.metadata.create_all(engine)

    print(f"Created {db_path.name} with tables:", ", ".join(Base.metadata.tables.keys()))
