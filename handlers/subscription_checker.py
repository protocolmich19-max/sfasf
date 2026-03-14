# handlers/subscription_checker.py
"""
Subscription checker & command binder (v2.2)
- Notifications tied per subscription (pay_metadatas.id) OR grace month.
- Flags set only on successful send; detailed logs.
- ✅ Now strictly considers only PAID subscriptions: PayMetadata.has_payed == True.
- Backwards-compatible exports for old imports.
"""

from __future__ import annotations

import threading
import time
import datetime as dt
import uuid
from typing import Optional, Tuple, NamedTuple

from sqlalchemy import (
    Column, Integer, String, Boolean, select, func, UniqueConstraint
)
from sqlalchemy.orm import Session
from telebot import types
from yookassa import Payment

from db.connect import engine
from db.models import (
    AutoPaymentMethod,
    Base,
    PayMetadata,
    PaymentRecord,
    User,
)  # PayMetadata: table 'pay_metadatas'


# === One-time notifications per subscription instance ===
class SubscriptionNoticeV2(Base):
    __tablename__ = "subscription_notices_v2"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    # NULL -> "grace" (first month for everyone), non-NULL -> PayMetadata.id
    pay_metadata_id = Column(Integer, nullable=True)

    sent_3d = Column(Boolean, default=False, nullable=False)
    sent_1d = Column(Boolean, default=False, nullable=False)
    sent_expired = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "pay_metadata_id", name="uq_notice_v2_user_pay"),
    )


AUTOPAY_RETRY_SECONDS = 3600  # seconds between automatic retry attempts
AUTOPAY_DEFAULT_AMOUNT = 333


def _init_tables() -> None:
    Base.metadata.create_all(engine)


def _now_utc_ts() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def _to_datetime(ts: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc)


def _latest_subscribe(session: Session, user_id: int) -> Optional[PayMetadata]:
    """
    Latest **PAID** PayMetadata where product starts with 'subscribe' (case-insensitive).
    """
    stmt = (
        select(PayMetadata)
        .where(PayMetadata.user_id == user_id)
        .where(PayMetadata.has_payed == True)  # only successful payments
        .where(func.lower(PayMetadata.product).like("subscribe%"))
        .order_by(PayMetadata.created_at.desc())  # created_at from Base
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


def _parse_subscribe_days(product: str) -> int:
    """
    Return duration in days for product name. Supports:
    - "subscribe-1", "subscribe 1" -> 30 days
    - "subscribe-12", "subscribe 12" -> 365 days
    - plain "subscribe*" -> 30 days default
    Non-subscribe returns 0.
    """
    name = (product or "").strip().lower()
    if not name.startswith("subscribe"):
        return 0
    # normalize separators to space
    normalized = name.replace("_", " ").replace("-", " ")
    parts = normalized.split()
    months = None
    for p in parts[1:]:
        if p.isdigit():
            months = int(p)
            break
    if months is None:
        months = 1
    if months >= 12:
        return 365
    return 30


def _expiry_from_product(created_at_ts: int, product: str) -> int:
    days = _parse_subscribe_days(product)
    if days <= 0:
        return 0
    return int(created_at_ts + days * 86400)


class SubContext(NamedTuple):
    expiry_ts: Optional[int]
    pay_metadata_id: Optional[int]  # None -> grace period
    is_grace: bool
    basis: str  # "grace" or "pay:<id>" or "-"


def _compute_subscription_context(session: Session, user: User) -> SubContext:
    """
    Compute expiry with stacking:
    - Base: everyone has a 30-day grace from user.created_at.
    - Then add durations of all paid subscriptions (product starts with 'subscribe'),
      ordered by created_at ascending, each extending from max(current_expiry, purchase_time).
    """
    basis = "-"

    # Base grace period
    expiry_ts: Optional[int] = None
    is_grace = False
    if getattr(user, "created_at", None):
        expiry_ts = int(user.created_at) + 30 * 86400
        is_grace = True

    # Fetch all PAID subscribe purchases ascending (to stack)
    pays = session.execute(
        select(PayMetadata)
        .where(PayMetadata.user_id == user.id)
        .where(PayMetadata.has_payed == True)
        .where(func.lower(PayMetadata.product).like("subscribe%"))
        .order_by(PayMetadata.created_at.asc())
    ).scalars().all()

    last_pay_id: Optional[int] = None
    for p in pays:
        created_at = int(getattr(p, "created_at", 0) or 0)
        days = _parse_subscribe_days(getattr(p, "product", "") or "")
        if days <= 0:
            continue
        start_from = created_at if expiry_ts is None else max(expiry_ts, created_at)
        expiry_ts = start_from + days * 86400
        is_grace = False  # once any paid sub applied, basis is paid
        last_pay_id = int(p.id)

    if expiry_ts is None:
        return SubContext(None, None, False, basis)

    basis = "grace" if is_grace else (f"pay:{last_pay_id}" if last_pay_id is not None else "-")
    return SubContext(expiry_ts, last_pay_id, is_grace, basis)


# === Autopay helpers ===
def _get_autopay_row(session: Session, user_id: int) -> Optional[AutoPaymentMethod]:
    return session.execute(
        select(AutoPaymentMethod).where(AutoPaymentMethod.user_id == user_id)
    ).scalar()


def _autopay_markup(session: Session, user_id: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    autopay_exists = _get_autopay_row(session, user_id) is not None
    button_text = "Отключить автоплатеж" if autopay_exists else "Подключить автоплатеж"
    callback_data = "subscribe-autopay-disable" if autopay_exists else "subscribe-autopay-enable"
    markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    markup.add(types.InlineKeyboardButton("Продлить подписку", callback_data="subscribe"))
    return markup


def _record_payment_reference(
    session: Session,
    user_id: int,
    pay_metadata_id: int,
    payment_id: Optional[str],
    product: str,
    amount_value: int,
) -> None:
    if not payment_id:
        return
    existing = session.execute(
        select(PaymentRecord).where(PaymentRecord.payment_id == payment_id)
    ).scalar()
    if existing is not None:
        return
    session.add(
        PaymentRecord(
            user_id=user_id,
            pay_metadata_id=pay_metadata_id,
            payment_id=payment_id,
            product=product,
            amount=amount_value,
        )
    )


def _maybe_trigger_autopay(session: Session, bot, user: User) -> bool:
    """
    Attempt to charge the stored payment method when subscription has expired.
    Returns True if an autopay attempt was initiated.
    """
    if user is None or not getattr(user, "id", None):
        return False

    autopay = _get_autopay_row(session, user.id)
    if autopay is None:
        return False

    now = _now_utc_ts()
    if autopay.last_attempt_at and now - int(autopay.last_attempt_at) < AUTOPAY_RETRY_SECONDS:
        return False

    # Avoid duplicate attempts if there is a pending autopay payment
    if autopay.last_payment_id:
        last_record = session.execute(
            select(PaymentRecord).where(PaymentRecord.payment_id == autopay.last_payment_id)
        ).scalar()
        if last_record:
            pending_metadata = session.execute(
                select(PayMetadata).where(PayMetadata.id == last_record.pay_metadata_id)
            ).scalar()
            if pending_metadata and pending_metadata.has_payed is False:
                return False

    amount_value = autopay.amount or AUTOPAY_DEFAULT_AMOUNT
    if amount_value <= 0:
        amount_value = AUTOPAY_DEFAULT_AMOUNT

    product = autopay.product or "subscribe-1"

    pay_metadata = PayMetadata(
        user_id=user.id,
        price=int(amount_value),
        product=product,
        procent_balance=50,
        inner_balance=0,
        has_payed=False,
    )
    session.add(pay_metadata)
    session.flush()

    idempotence_key = str(uuid.uuid4())
    payment_request = {
        "amount": {
            "value": str(amount_value),
            "currency": "RUB",
        },
        "capture": True,
        "description": f"Ежемесячный автоплатеж для пользователя {user.id}",
        "payment_method_id": autopay.payment_method_id,
        "metadata": {
            "orderNumber": pay_metadata.id,
            "autopay": True,
        },
    }

    autopay.last_attempt_at = now

    try:
        payment = Payment.create(payment_request, idempotency_key=idempotence_key)
    except Exception as exc:
        try:
            bot.send_message(
                user.tg_id,
                "Не удалось выполнить автопродление подписки. "
                "Попробуйте оплатить подписку вручную.\n\n"
                f"Техническая информация: {exc}",
            )
        except Exception:
            pass
        return False

    payment_id = getattr(payment, "id", None)
    if payment_id:
        autopay.last_payment_id = payment_id
        _record_payment_reference(session, user.id, pay_metadata.id, payment_id, product, int(amount_value))

    try:
        bot.send_message(
            user.tg_id,
            "Срок подписки истёк, запускаем автопродление. "
            "Мы сообщим, как только оплата подтвердится.",
            reply_markup=_autopay_markup(session, user.id),
        )
    except Exception:
        pass

    return True


# === Public API ===
def has_active_subscription(session: Session, user_id: int) -> bool:
    user = session.execute(select(User).where(User.id == user_id)).scalar()
    if not user:
        return False
    ctx = _compute_subscription_context(session, user)
    return bool(ctx.expiry_ts and _now_utc_ts() < ctx.expiry_ts)


def get_subscription_days_left(session: Session, user_id: int) -> Optional[int]:
    """
    Returns remaining whole days (>=0) until expiry, or None if no subscription.
    """
    user = session.execute(select(User).where(User.id == user_id)).scalar()
    if not user:
        return None
    ctx = _compute_subscription_context(session, user)
    if not ctx.expiry_ts:
        return None
    seconds_left = ctx.expiry_ts - _now_utc_ts()
    if seconds_left < 0:
        return 0
    return int(seconds_left // 86400)


def format_subscription_remaining(days_left: Optional[int]) -> str:
    """
    Human-friendly: X дн., Y мес., Z г. (с округлением до ближайшей единицы).
    """
    if days_left is None:
        return "нет активной подписки"
    if days_left <= 0:
        return "подписка истекла"
    # Convert to months/years approximately
    years = days_left // 365
    rem_days = days_left % 365
    months = rem_days // 30
    days = rem_days % 30
    parts = []
    if years > 0:
        parts.append(f"{years} г.")
    if months > 0:
        parts.append(f"{months} мес.")
    if days > 0 and years == 0:  # show days only when less than a year for brevity
        parts.append(f"{days} дн.")
    return " ".join(parts) if parts else "менее 1 дня"


def has_active_subscription_handler(user_id: int) -> bool:
    with Session(engine) as session:
        return has_active_subscription(session, user_id)


# === Notices helpers ===
def _get_or_create_notice_v2(session: Session, user_id: int, pay_metadata_id: Optional[int]) -> SubscriptionNoticeV2:
    row = session.execute(
        select(SubscriptionNoticeV2).where(
            SubscriptionNoticeV2.user_id == user_id,
            SubscriptionNoticeV2.pay_metadata_id.is_(pay_metadata_id) if pay_metadata_id is None else
            SubscriptionNoticeV2.pay_metadata_id == pay_metadata_id
        )
    ).scalar()

    if row is None:
        row = SubscriptionNoticeV2(user_id=user_id, pay_metadata_id=pay_metadata_id)
        session.add(row)
        session.flush()
    return row


# === Telegram send wrapper ===
def _send_once(bot, chat_id: int, text: str, reply_markup=None) -> bool:
    try:
        bot.send_message(chat_id, text, reply_markup=reply_markup)
        print(f"[subs] sent -> chat_id={chat_id}")
        return True
    except Exception as e:
        print(f"[subs] send FAILED -> chat_id={chat_id} error={e}")
        return False


# === Product texts ===
TEXT_3D = (
    "💌 Любовь любит заботу.\n"
    "Ваша подписка действует ещё 3 дня.\n"
    "Продлите её — и пусть пространство любви и вдохновения остаётся с вами."
)

TEXT_1D = (
    "Завтра доступ к системе «За любовь» может прерваться .\n"
    "А мы так хотим, чтобы вы продолжали получать поддержку, тепло и новые открытия.\n"
    "Успейте продлить ❤️"
)

TEXT_EXPIRED = (
"""💌 Доступ временно приостановлен

Похоже, срок вашей подписки закончился.
Чтобы оставаться в пространстве любви, получать напоминания, задания и доступ к новым материалам — нужно продлить подписку 🌿

✨ Оплатите подписку, и бот снова откроет все разделы.
Вы — важная часть движения 💛"""
)


def check_and_notify_subscriptions(bot) -> Tuple[int, int, int]:
    """
    Walk over users, send at most ONE message per threshold per *subscription instance*.
    Returns (sent_3d, sent_1d, sent_expired).
    """
    _init_tables()
    c3 = c1 = ce = 0

    with Session(engine) as session:
        users = session.execute(select(User)).scalars().all()
        for user in users:
            chat_id = getattr(user, "tg_id", None)
            if not chat_id:
                continue

            ctx = _compute_subscription_context(session, user)
            print(f"[subs] user_id={user.id} chat_id={chat_id} basis={ctx.basis} "
                  f"expiry={_to_datetime(ctx.expiry_ts).isoformat() if ctx.expiry_ts else None}")

            # No subscription at all -> expired once on (user, None)
            if ctx.expiry_ts is None:
                notice = _get_or_create_notice_v2(session, user.id, None)
                if not notice.sent_expired:
                    if _send_once(bot, chat_id, TEXT_EXPIRED, reply_markup=_autopay_markup(session, user.id)):
                        notice.sent_expired = True
                        ce += 1
                continue

            days_left = (ctx.expiry_ts - _now_utc_ts()) / 86400.0
            notice = _get_or_create_notice_v2(session, user.id, ctx.pay_metadata_id)  # None -> grace, ID -> paid

            if 0 < days_left <= 3 and not notice.sent_3d:
                if _send_once(bot, chat_id, TEXT_3D, reply_markup=_autopay_markup(session, user.id)):
                    notice.sent_3d = True
                    c3 += 1

            if 0 < days_left <= 1 and not notice.sent_1d:
                if _send_once(bot, chat_id, TEXT_1D, reply_markup=_autopay_markup(session, user.id)):
                    notice.sent_1d = True
                    c1 += 1

            if days_left <= 0:
                triggered = _maybe_trigger_autopay(session, bot, user)
                if not notice.sent_expired:
                    if triggered:
                        notice.sent_expired = True
                        ce += 1
                    elif _send_once(bot, chat_id, TEXT_EXPIRED, reply_markup=_autopay_markup(session, user.id)):
                        notice.sent_expired = True
                        ce += 1

        session.commit()

    return (c3, c1, ce)


# === Integration helpers ===
def bind_subscription_commands(bot):
    """
    Register commands and a debug helper.
    """
    from telebot import types

    aliases = ["SlashCheckSubs", "check_subs", "checksubs"]

    @bot.message_handler(commands=aliases + [a.lower() for a in aliases])
    def _cmd(m: types.Message):
        c3, c1, ce = check_and_notify_subscriptions(bot)
        bot.reply_to(m, f"Проверка выполнена: 3д={c3}, 1д={c1}, истекло={ce}")

    @bot.message_handler(commands=["debug_subs"])
    def _dbg(m: types.Message):
        try:
            arg = m.text.split(maxsplit=1)[1].strip()
            uid = int(arg)
        except Exception:
            bot.reply_to(m, "Укажи user_id: /debug_subs 3")
            return
        with Session(engine) as session:
            user = session.execute(select(User).where(User.id == uid)).scalar()
            if not user:
                bot.reply_to(m, f"User #{uid} не найден")
                return
            ctx = _compute_subscription_context(session, user)
            days_left = None if ctx.expiry_ts is None else round((ctx.expiry_ts - _now_utc_ts()) / 86400.0, 3)

            # Also show last PAID subscribe row id (if any)
            last_paid = _latest_subscribe(session, uid)
            last_paid_id = getattr(last_paid, "id", None)
            last_paid_created = getattr(last_paid, "created_at", None)
            last_paid_product = getattr(last_paid, "product", None)

            bot.reply_to(
                m,
                f"user_id={uid}\nchat_id={user.tg_id}\nbasis={ctx.basis}\n"
                f"expiry={_to_datetime(ctx.expiry_ts).strftime('%Y-%m-%d %H:%M:%S') if ctx.expiry_ts else None}\n"
                f"days_left={days_left}\n"
                f"last_paid_id={last_paid_id} product={last_paid_product} created_at={last_paid_created}"
            )

    # Fallback by plain text
    @bot.message_handler(func=lambda msg: isinstance(getattr(msg, "text", None), str) and msg.text.strip().lower() in {
        "/slashchecksubs", "slashchecksubs", "/checksubs", "checksubs", "/check_subs", "check_subs"
    })
    def _fallback(m: types.Message):
        c3, c1, ce = check_and_notify_subscriptions(bot)
        bot.reply_to(m, f"Проверка выполнена: 3д={c3}, 1д={c1}, истекло={ce}")


def _loop_worker(bot, interval_seconds: int):
    while True:
        try:
            check_and_notify_subscriptions(bot)
        except Exception as e:
            print("[subs] loop error:", e)
        time.sleep(interval_seconds)


def integrate_subscription_scheduler(bot, interval_seconds: int = 3600):
    """
    Start the hourly scanner.
    """
    t = threading.Thread(target=_loop_worker, args=(bot, interval_seconds), daemon=True)
    t.start()


# --- Backwards-compatible names for existing imports ---
start_subscription_scheduler = integrate_subscription_scheduler
register_manual_handler = bind_subscription_commands
