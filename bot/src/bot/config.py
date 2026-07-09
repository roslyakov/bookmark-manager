from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str
    """Public HTTPS URL Telegram should POST updates to, e.g.
    https://bookmarks.example.com/telegram/webhook"""
    telegram_webhook_secret: str = ""
    """Secret token Telegram includes in the X-Telegram-Bot-Api-Secret-Token
    header on every webhook request; used to validate requests actually come
    from Telegram (REQUIREMENTS.md §11: validate Telegram webhook requests)."""
    telegram_webhook_path: str = "/telegram/webhook"

    # Web app
    app_base_url: str

    # Auth
    auth_token_ttl_minutes: int = 15

    # Server
    bot_http_host: str = "0.0.0.0"
    bot_http_port: int = 8080


def get_bot_settings() -> BotSettings:
    return BotSettings()  # type: ignore[call-arg]
