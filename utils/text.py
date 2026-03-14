"""
Утилиты для работы с текстом
"""
import html
from typing import Optional


def escape_html(text: Optional[str]) -> str:
    """
    Экранирует HTML-символы в тексте для безопасной отправки в Telegram.
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    return html.escape(text or "")


def format_user_mention(user, fallback_tg_id: Optional[int] = None) -> str:
    """
    Форматирует упоминание пользователя для отображения.
    
    Args:
        user: Объект пользователя из БД
        fallback_tg_id: Telegram ID для использования, если username отсутствует
        
    Returns:
        Строка с упоминанием пользователя (@username или id 123456)
    """
    if user and hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    if fallback_tg_id:
        return f"id {fallback_tg_id}"
    if user and hasattr(user, 'tg_id') and user.tg_id:
        return f"id {user.tg_id}"
    return "пользователь"

