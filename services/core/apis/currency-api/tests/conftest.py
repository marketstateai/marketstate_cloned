import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.rates import get_rates_service
from app.db.models import Base, ExchangeRate
from app.main import app
from app.services.rates_service import RatesService

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=engine)


def override_get_rates_service():
    db = TestingSessionLocal()
    try:
        yield RatesService(db=db)
    finally:
        db.close()


app.dependency_overrides[get_rates_service] = override_get_rates_service


@pytest.fixture(autouse=True)
def reset_db():
    db = TestingSessionLocal()
    try:
        db.query(ExchangeRate).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
