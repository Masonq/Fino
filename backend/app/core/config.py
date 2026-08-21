from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PLONK"
    database_url: str = "postgresql://fino:fino@localhost:5432/fino"
    secret_key: str = "change-me-in-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    default_languages: list[str] = ["ru", "en", "sr"]
    media_dir: str = "./media"

    # Почта для кодов подтверждения (пока не задана — коды пишутся в журнал)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "PLONK <noreply@plonk.rs>"

    # Telegram-бот для кодов и уведомлений
    telegram_bot_token: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
