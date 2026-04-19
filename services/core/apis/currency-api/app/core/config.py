from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Currency API"
    env: str = Field(default="dev")
    api_prefix: str = "/api/v1"

    database_url: str | None = None
    sqlite_path: str = "dev_data/currency.db"

    allowed_hosts: str = "*"
    cors_origins: str = ""
    rate_limit_per_minute: int = 5
    api_auth_token: str = "dev-token-change-me"

    seed_data_path: str = "tests/currencies.json"
    seed_on_startup: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = Path(self.sqlite_path)
        return f"sqlite:///{db_path.resolve()}"

    @property
    def is_sqlite(self) -> bool:
        return self.db_url.startswith("sqlite")

    @property
    def parsed_allowed_hosts(self) -> list[str]:
        values = [v.strip() for v in self.allowed_hosts.split(",") if v.strip()]
        return values or ["*"]

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [v.strip() for v in self.cors_origins.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
