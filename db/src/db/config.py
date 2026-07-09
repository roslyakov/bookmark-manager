from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection configuration, shared by db/bot/worker.

    DATABASE_URL should use the asyncpg driver, e.g.:
        postgresql+asyncpg://user:password@host:5432/dbname
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]
