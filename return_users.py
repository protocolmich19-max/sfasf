from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
import asyncio
import json

# Получите ключи API и секретный ключ для работы с API Telegram.
# Для этого нужно зарегистрировать свое приложение на сайте https://my.telegram.org/auth.
api_id = 24278864
api_hash = 'fe33bfa122ca4c911269f1f0202c6ebc'

# Создайте экземпляр клиента Telethon:
client = TelegramClient(
    'GiftsToPortalRobot',
    api_id,
    api_hash,
    device_model="Google Pixel 7 Pro",
    system_version="SDK 33",
    app_version="11.2.3",
    lang_code="de",
    system_lang_code="de",
)


async def get_channel_users(channel):
    offset = 0
    limit = 100
    all_users = []

    first_page_dumped = False

    while True:
        result = await client(
            GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=limit,
                hash=0,
            )
        )

        # Сохраним сырой ответ первой страницы для отладки
        if not first_page_dumped:
            try:
                with open("return_users2.txt", 'w', encoding='utf-8') as file:
                    file.write(str(result))
            except Exception:
                pass
            first_page_dumped = True

        users_page = getattr(result, 'users', [])
        if not users_page:
            break

        all_users.extend(users_page)
        offset += len(users_page)

        if len(users_page) < limit:
            break

    return all_users


async def main():
    # Подключимся и получим сущность канала
    await client.start()
    channel = await client.get_entity('za_lyubov_igra')

    users = await get_channel_users(channel)

    # Подготовим JSON-структуру
    records = []
    for user in users:
        first_name = (getattr(user, 'first_name', '') or '').strip()
        last_name = (getattr(user, 'last_name', '') or '').strip()
        full_name = f"{first_name} {last_name}".strip()
        username = getattr(user, 'username', None)
        records.append({
            'tg_id': getattr(user, 'id', None),
            'full_name': full_name,
            'username': username,
        })

    # Сохраним JSON
    try:
        with open("return_users.json", 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Краткий вывод в консоль
    for r in records[:10]:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())