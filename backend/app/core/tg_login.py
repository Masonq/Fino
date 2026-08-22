"""
Вход в Telegram и список доступных чатов.

Запускается один раз руками: Telegram пришлёт код в приложение, после чего
рядом появится файл сессии и код больше не понадобится. Тем же запуском
печатаем чаты, где состоит аккаунт, — по ним настраивается, откуда читать.

    python3 -m app.core.tg_login

Файл сессии равнозначен доступу к аккаунту, поэтому лежит только на сервере
и в репозиторий не попадает.
"""
import asyncio

from telethon import TelegramClient

from app.core.config import settings


async def main() -> None:
    if not settings.tg_api_id or not settings.tg_api_hash:
        print("Не заданы TG_API_ID и TG_API_HASH в .env")
        return

    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    me = await client.get_me()
    print(f"Вошли как: {me.first_name} (@{me.username or 'без ника'})\n")

    print("Группы и каналы, доступные аккаунту:\n")
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
        entity = dialog.entity
        # id и признак «с темами» нужны, чтобы читать разделы по отдельности
        forum = getattr(entity, "forum", False)
        print(f"  {dialog.id:>16}  {'темы' if forum else '    '}  {dialog.name}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
