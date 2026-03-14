import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Iterable, List, Optional, Set, Tuple

import requests

# =========================
# Настройки для пользователя
# Укажите текст сообщения и путь к картинке здесь.
# Если IMAGE_PATH пустой, будет отправлено обычное текстовое сообщение.
# Если IMAGE_PATH указан, будет отправлена фотография с подписью.
MESSAGE_TEXT = """
Темные не спят🙈
Что в очередной раз подтверждает, что мы с Вами создаем что то очень важное!

Привет Дорогие ! 
На связи Артем Николаев и Ксюша Душанова 🙌
Пришло и наше с вами время "проверить" наши отношения и намерения на прочность) 

Переведя на земной язык, при обновлении системы, произошел непредвиденный сбой. 

От слов к делу, сделайте, пожалуйста, 2 простых действия : 

1️⃣ Зайдите в бот (https://t.me/forlove2025_bot) и перезапустите его, написав вручную " /start ", затем повторно выберите город и введите номер телефона

2️⃣ Скопируйте ник своего пригласителя, в разделе "партнерская программа" , нажмите кнопку "сменить пригласителя" и внесите скопированный ник

По любым вопросам вы можете обратится в тех поддержку.

❤️До 15 октября наш рук-ль IT отдела проведет несколько открытых брифингов и окажет вам практическую помощь.

Ваша приверженность и участие имеют для нас сейчас значение, как никогда.
С любовью❤️
Ваши Артем и Ксюша"""  # Например: "Привет! Подписывайся на наш канал"
IMAGE_PATH = "./return_users.jpg"     # Например: r"assets\subscribe-img.png" или "D:/path/to/image.jpg"
# =========================


def read_broadcast_text(arg_text: Optional[str], text_file: Optional[str]) -> str:
    # Приоритет: константа сверху файла -> --text -> --text-file -> message.txt
    if isinstance(MESSAGE_TEXT, str) and MESSAGE_TEXT.strip():
        return MESSAGE_TEXT.strip()
    if arg_text:
        return arg_text
    if text_file:
        with open(text_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    default_file = 'message.txt'
    if os.path.exists(default_file):
        with open(default_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    raise ValueError('No message text provided. Use --text or --text-file or create message.txt')


def load_user_ids(json_path: str) -> List[int]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ids: List[int] = []
    for item in data:
        tg_id = item.get('tg_id')
        if isinstance(tg_id, int):
            ids.append(tg_id)
        elif isinstance(tg_id, str) and tg_id.isdigit():
            ids.append(int(tg_id))
    return ids


def load_already_sent(path: str) -> Set[int]:
    if not os.path.exists(path):
        return set()
    ids: Set[int] = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.isdigit():
                ids.add(int(line))
    return ids


def append_sent(path: str, chat_id: int) -> None:
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"{chat_id}\n")


def log_result(path: str, message: str) -> None:
    timestamp = datetime.utcnow().isoformat()
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")


def send_message(session: requests.Session, token: str, chat_id: int, text: str, parse_mode: Optional[str], disable_notification: bool) -> Tuple[bool, Optional[str]]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_notification': disable_notification,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        resp = session.post(url, json=payload, timeout=20)
    except requests.RequestException as e:
        return False, f"network_error: {e}"

    if resp.status_code == 200:
        j = resp.json()
        ok = j.get('ok', False)
        if ok:
            return True, None
        # unexpected: ok=false but 200
        return False, f"api_error: {j}"

    # Handle rate limit 429
    if resp.status_code == 429:
        try:
            j = resp.json()
            retry_after = j.get('parameters', {}).get('retry_after', 1)
        except Exception:
            retry_after = 1
        return False, f"rate_limited:{retry_after}"

    # Common errors: 403 (bot was blocked by the user), 400 (bad request)
    try:
        j = resp.json()
    except Exception:
        j = {'text': resp.text}
    return False, f"http_{resp.status_code}:{j}"


def send_photo(session: requests.Session, token: str, chat_id: int, photo_path: str, caption: Optional[str], parse_mode: Optional[str], disable_notification: bool) -> Tuple[bool, Optional[str]]:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    data = {
        'chat_id': str(chat_id),
        'disable_notification': str(disable_notification).lower(),
    }
    if caption:
        data['caption'] = caption
    if parse_mode:
        data['parse_mode'] = parse_mode

    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': (os.path.basename(photo_path), f)}
            resp = session.post(url, data=data, files=files, timeout=30)
    except FileNotFoundError:
        return False, f"file_not_found:{photo_path}"
    except requests.RequestException as e:
        return False, f"network_error: {e}"

    if resp.status_code == 200:
        j = resp.json()
        ok = j.get('ok', False)
        if ok:
            return True, None
        return False, f"api_error: {j}"

    if resp.status_code == 429:
        try:
            j = resp.json()
            retry_after = j.get('parameters', {}).get('retry_after', 1)
        except Exception:
            retry_after = 1
        return False, f"rate_limited:{retry_after}"

    try:
        j = resp.json()
    except Exception:
        j = {'text': resp.text}
    return False, f"http_{resp.status_code}:{j}"


def iterate_with_limits(ids: Iterable[int], offset: int, limit: Optional[int]) -> List[int]:
    ids_list = list(ids)
    sliced = ids_list[offset:]
    if limit is not None:
        sliced = sliced[:limit]
    return sliced


def main() -> None:
    parser = argparse.ArgumentParser(description='Send broadcast to users from return_users.json')
    parser.add_argument('--token', required=False, default=os.getenv('TELEGRAM_BOT_TOKEN'), help='Bot token (or set TELEGRAM_BOT_TOKEN)')
    parser.add_argument('--json', default='return_users.json', help='Path to JSON file with users')
    parser.add_argument('--text', help='Message text to send (overrides top constant if set)')
    parser.add_argument('--text-file', dest='text_file', help='Path to file with message text')
    parser.add_argument('--image', dest='image_path', default=None, help='Path to image (overrides top constant if set)')
    parser.add_argument('--parse-mode', dest='parse_mode', default=None, choices=['Markdown', 'MarkdownV2', 'HTML'], help='Telegram parse mode')
    parser.add_argument('--disable-notification', action='store_true', help='Send silently')
    parser.add_argument('--offset', type=int, default=0, help='Start index in user list')
    parser.add_argument('--limit', type=int, default=None, help='Max users to send')
    parser.add_argument('--sleep', type=float, default=0.06, help='Delay between sends (seconds)')
    parser.add_argument('--dry-run', action='store_true', help='Do not send, just print planned recipients')
    parser.add_argument('--resume-file', default='broadcast_sent.txt', help='Track sent user ids for resume')
    parser.add_argument('--log-file', default='broadcast_results.log', help='Log results here')
    parser.add_argument('--fail-file', default='broadcast_failed.txt', help='Write failed ids here')
    args = parser.parse_args()

    if not args.token:
        print('ERROR: --token is required (or set TELEGRAM_BOT_TOKEN)')
        sys.exit(1)

    try:
        text = read_broadcast_text(args.text, args.text_file)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    try:
        ids = load_user_ids(args.json)
    except Exception as e:
        print(f'ERROR: failed to read {args.json}: {e}')
        sys.exit(1)

    # Deduplicate while preserving order
    seen: Set[int] = set()
    unique_ids: List[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique_ids.append(i)

    # Resume support: skip already sent
    already_sent = load_already_sent(args.resume_file)
    remaining = [i for i in unique_ids if i not in already_sent]
    remaining = iterate_with_limits(remaining, args.offset, args.limit)

    print(f"Total in file: {len(ids)} | Unique: {len(unique_ids)} | Already sent: {len(already_sent)} | To send now: {len(remaining)}")

    if args.dry_run:
        print('Dry run. First 20 ids:')
        print(remaining[:20])
        return

    session = requests.Session()

    # Определим, что отправлять: фото или текст
    image_path_cfg = IMAGE_PATH.strip() if isinstance(IMAGE_PATH, str) else ""
    image_path = args.image_path or image_path_cfg or ""

    for idx, chat_id in enumerate(remaining, start=1):
        if image_path:
            ok, err = send_photo(session, args.token, chat_id, image_path, text, args.parse_mode, args.disable_notification)
        else:
            ok, err = send_message(session, args.token, chat_id, text, args.parse_mode, args.disable_notification)

        if ok:
            append_sent(args.resume_file, chat_id)
            log_result(args.log_file, f"OK chat_id={chat_id}")
        else:
            # Handle rate limiting with backoff if needed
            if err and err.startswith('rate_limited:'):
                try:
                    retry_after = int(err.split(':', 1)[1])
                except Exception:
                    retry_after = 1
                log_result(args.log_file, f"RATE_LIMIT chat_id={chat_id} retry_after={retry_after}s")
                time.sleep(retry_after + 1)
                # One retry after sleeping
                ok_retry, err_retry = send_message(session, args.token, chat_id, text, args.parse_mode, args.disable_notification)
                if ok_retry:
                    append_sent(args.resume_file, chat_id)
                    log_result(args.log_file, f"OK_AFTER_RETRY chat_id={chat_id}")
                else:
                    log_result(args.log_file, f"FAIL_AFTER_RETRY chat_id={chat_id} err={err_retry}")
                    with open(args.fail_file, 'a', encoding='utf-8') as ff:
                        ff.write(f"{chat_id}\n")
            else:
                log_result(args.log_file, f"FAIL chat_id={chat_id} err={err}")
                with open(args.fail_file, 'a', encoding='utf-8') as ff:
                    ff.write(f"{chat_id}\n")

        # Gentle pacing to avoid flood limits (and per-chat 1 msg/sec is respected by TG)
        time.sleep(args.sleep)

        if idx % 100 == 0:
            print(f"Progress: sent/attempted {idx}/{len(remaining)}")

    print('Done.')


if __name__ == '__main__':
    main()


