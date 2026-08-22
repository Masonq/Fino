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
    # свой сервер перевода — без ограничений по количеству запросов
    translate_url: str | None = None

    # Нейросеть для заголовков там, где правила не справились. Ключ
    # бесплатный, берётся в Google AI Studio; без ключа парсер работает
    # как прежде, только на правилах.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    # Запасной провайдер: тоже бесплатный, но с более тесным лимитом по
    # токенам в минуту.
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    # Сколько объявлений за один заход отдаём модели: бесплатный тариф
    # ограничен по суткам, и тратить его весь на один прогон незачем.
    ai_titles_per_run: int = 120

    # Чтение барахолок в Telegram. Ключи с my.telegram.org, телефон — того
    # аккаунта, который состоит в этих чатах. Сессия лежит рядом файлом,
    # так что код подтверждения запрашивается только при первом входе.
    tg_api_id: int | None = None
    tg_api_hash: str | None = None
    tg_phone: str | None = None
    tg_session: str = "tg.session"

    # Адрес, по которому сайт забирает файлы. Загрузки с сайта записывают
    # полный адрес, потому что фронтенд и бэкенд отвечают на разных портах,
    # и относительный «/media/...» ушёл бы не туда. Импорту брать этот
    # адрес неоткуда — задаём здесь.
    public_base_url: str = "http://89.208.113.147:8002"

    class Config:
        env_file = ".env"


settings = Settings()
