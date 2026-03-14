"""
Утилиты для отправки медиа-файлов в Telegram
"""
import os
from typing import Optional, Callable
from telebot import TeleBot
import config


def send_media(
    bot: TeleBot,
    chat_id: int,
    media_path: Optional[str],
    sender: Callable,
    **kwargs
) -> None:
    """
    Отправляет медиа-файл (фото, видео, документ) в чат.
    
    Поддерживает как локальные файлы, так и URL.
    
    Args:
        bot: Экземпляр Telegram бота
        chat_id: ID чата для отправки
        media_path: Путь к файлу или URL
        sender: Функция отправки (bot.send_photo, bot.send_video, bot.send_document)
        **kwargs: Дополнительные параметры для функции отправки
    """
    if not media_path:
        return
    
    # Если это URL
    if isinstance(media_path, str) and media_path.startswith(("http://", "https://")):
        try:
            sender(chat_id, media_path, **kwargs)
        except Exception as exc:
            try:
                print(f"[media] failed to send remote media {media_path}: {exc}")
            except Exception:
                pass
        return
    
    # Если это локальный файл
    full_path = media_path
    if isinstance(media_path, str) and not os.path.isabs(media_path):
        full_path = os.path.normpath(os.path.join(config.PROJECT_ROOT, media_path))
    
    try:
        with open(full_path, "rb") as media_file:
            sender(chat_id, media_file, **kwargs)
    except FileNotFoundError:
        try:
            print(f"[media] media file not found: {full_path}")
        except Exception:
            pass
    except Exception as exc:
        try:
            print(f"[media] failed to send media {full_path}: {exc}")
        except Exception:
            pass

