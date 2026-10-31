from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MyAIStats"
    version: str = "0.2.3"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/myaistats.db"
    secret_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_currency: str = "USD"
    demo_mode: bool = True

    sync_usage_interval_minutes: int = 15
    sync_costs_interval_minutes: int = 30
    sync_balances_interval_minutes: int = 30
    sync_pricing_interval_minutes: int = 1440

    model_config = SettingsConfigDict(
        env_prefix="MYAISTATS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def data_dir(self) -> Path:
        path = Path("./data")
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
