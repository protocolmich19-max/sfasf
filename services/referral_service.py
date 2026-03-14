"""
Сервис для работы с реферальной системой
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
from db.models import User, PayMetadata
from utils.referral import (
    get_ref_level_requirement,
    get_ref_percent,
    get_ref_inner_percent,
)
import config


def get_user_referrer(session: Session, user: User) -> User:
    """
    Получает реферера пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        
    Returns:
        Объект реферера
    """
    if user.ref == 1:
        # Если ref = 1, это системный админ
        return session.execute(select(User).where(User.id == 1)).scalar()
    return session.execute(select(User).where(User.tg_id == user.ref)).scalar()


def get_referral_chain(session: Session, users: List[User]) -> List[User]:
    """
    Получает следующий уровень реферальной цепочки.
    
    Args:
        session: Сессия БД
        users: Список пользователей текущего уровня
        
    Returns:
        Список пользователей следующего уровня
    """
    if not users:
        return []
    
    tg_ids = [user.tg_id for user in users if user.tg_id]
    if not tg_ids:
        return []
    
    return list(session.execute(
        select(User).where(User.ref.in_(tg_ids)).where(User.ref != 1)
    ).scalars().all())


def distribute_referral_rewards(
    session: Session,
    user: User,
    pay_metadata: PayMetadata,
    max_lines: int = 20
) -> None:
    """
    Распределяет реферальные вознаграждения по цепочке рефереров.
    
    Args:
        session: Сессия БД
        user: Пользователь, совершивший покупку
        pay_metadata: Метаданные платежа
        max_lines: Максимальное количество линий для распределения
    """
    if user.ref is None:
        session.commit()
        return
    
    admin_user = session.execute(select(User).where(User.id == 1)).scalar()
    if not admin_user:
        return
    
    total_ref_amount = pay_metadata.price * (pay_metadata.procent_balance / 100)
    total_inner_amount = pay_metadata.price * (pay_metadata.inner_balance / 100)
    
    current_referrer = get_user_referrer(session, user)
    
    for line in range(1, max_lines + 1):
        if current_referrer is None:
            break
        
        required_level = get_ref_level_requirement(line)
        ref_percent = get_ref_percent(line)
        inner_percent = get_ref_inner_percent(line)
        
        ref_amount = round(total_ref_amount * ref_percent / 100, 2)
        inner_amount = total_inner_amount * inner_percent / 100
        
        if current_referrer.ref_level >= required_level:
            current_referrer.balance += ref_amount
            current_referrer.inner_balance += inner_amount
        else:
            admin_user.inner_balance += inner_amount
            admin_user.balance += ref_amount
        
        current_referrer = get_user_referrer(session, current_referrer)
    
    session.commit()

