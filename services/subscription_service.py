"""
Сервис для работы с подписками
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from db.models import User, PayMetadata


def parse_subscription_duration(product: str) -> int:
    """
    Определяет длительность подписки в днях по названию продукта.
    
    Args:
        product: Название продукта (например, "subscribe-1" или "subscribe-12")
        
    Returns:
        Количество дней подписки (30 для месяца, 365 для года)
    """
    name = (product or "").strip().lower()
    if not name.startswith("subscribe"):
        return 0
    
    normalized = name.replace("_", " ").replace("-", " ")
    parts = normalized.split()
    months = None
    
    for p in parts[1:]:
        if p.isdigit():
            months = int(p)
            break
    
    if months is None:
        months = 1
    
    return 365 if months >= 12 else 30


def get_subscription_expiry(session: Session, user: User) -> Optional[int]:
    """
    Вычисляет дату окончания подписки пользователя с учетом всех оплаченных подписок.
    
    Args:
        session: Сессия БД
        user: Пользователь
        
    Returns:
        Unix timestamp даты окончания подписки или None
    """
    # Базовый grace период 30 дней с момента регистрации
    expiry_ts: Optional[int] = None
    if hasattr(user, "created_at") and user.created_at:
        expiry_ts = int(user.created_at) + 30 * 86400
    
    # Получаем все оплаченные подписки
    subscriptions = session.execute(
        select(PayMetadata)
        .where(PayMetadata.user_id == user.id)
        .where(PayMetadata.has_payed == True)
        .where(func.lower(PayMetadata.product).like("subscribe%"))
        .order_by(PayMetadata.created_at.asc())
    ).scalars().all()
    
    # Складываем длительности подписок
    for sub in subscriptions:
        created_at = int(getattr(sub, "created_at", 0) or 0)
        days = parse_subscription_duration(getattr(sub, "product", "") or "")
        
        if days <= 0:
            continue
        
        start_from = created_at if expiry_ts is None else max(expiry_ts, created_at)
        expiry_ts = start_from + days * 86400
    
    return expiry_ts


def has_active_subscription(session: Session, user_id: int) -> bool:
    """
    Проверяет, есть ли у пользователя активная подписка.
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        
    Returns:
        True, если подписка активна
    """
    user = session.execute(select(User).where(User.id == user_id)).scalar()
    if not user:
        return False
    
    expiry = get_subscription_expiry(session, user)
    if not expiry:
        return False
    
    now = int(datetime.now(timezone.utc).timestamp())
    return now < expiry


def get_subscription_days_left(session: Session, user_id: int) -> Optional[int]:
    """
    Возвращает количество оставшихся дней подписки.
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        
    Returns:
        Количество дней или None, если подписки нет
    """
    user = session.execute(select(User).where(User.id == user_id)).scalar()
    if not user:
        return None
    
    expiry = get_subscription_expiry(session, user)
    if not expiry:
        return None
    
    now = int(datetime.now(timezone.utc).timestamp())
    seconds_left = expiry - now
    
    if seconds_left < 0:
        return 0
    
    return int(seconds_left // 86400)


def format_subscription_remaining(days_left: Optional[int]) -> str:
    """
    Форматирует оставшееся время подписки в читаемый вид.
    
    Args:
        days_left: Количество дней
        
    Returns:
        Отформатированная строка (например, "2 мес. 15 дн.")
    """
    if days_left is None:
        return "нет активной подписки"
    if days_left <= 0:
        return "подписка истекла"
    
    years = days_left // 365
    rem_days = days_left % 365
    months = rem_days // 30
    days = rem_days % 30
    
    parts = []
    if years > 0:
        parts.append(f"{years} г.")
    if months > 0:
        parts.append(f"{months} мес.")
    if days > 0 and years == 0:
        parts.append(f"{days} дн.")
    
    return " ".join(parts) if parts else "менее 1 дня"

