from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Fino"
    database_url: str = "postgresql://fino:fino@localhost:5432/fino"
    secret_key: str = "change-me-in-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    default_languages: list[str] = ["ru", "en", "sr"]
    media_dir: str = "./media"

    class Config:
        env_file = ".env"


settings = Settings()
