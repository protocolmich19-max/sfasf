from sqlalchemy import select
from sqlalchemy.orm import Session

from db.connect import engine
from db.models import AutoPaymentMethod, PaymentRecord, User


def get_user(session: Session, tg_id: int):
    user = session.execute(select(User).where(User.tg_id == tg_id)).scalar()
    return user


def create_user(session: Session, tg_id: int, full_name: str, username: str, ref: str = 1):
    user = User(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        phone="",
        city="",
        ref=ref,
    )

    session.add(user)
    session.commit()

    return user


def get_autopay_method(session: Session, user_id: int) -> AutoPaymentMethod | None:
    return session.execute(
        select(AutoPaymentMethod).where(AutoPaymentMethod.user_id == user_id)
    ).scalar()


def upsert_autopay_method(
    session: Session,
    user_id: int,
    payment_method_id: str,
    product: str,
    amount: int,
    payment_id: str | None = None,
) -> AutoPaymentMethod:
    autopay = get_autopay_method(session, user_id)
    if autopay is None:
        autopay = AutoPaymentMethod(
            user_id=user_id,
            payment_method_id=payment_method_id,
            product=product,
            amount=amount,
            last_payment_id=payment_id,
        )
        session.add(autopay)
    else:
        autopay.payment_method_id = payment_method_id
        autopay.product = product
        autopay.amount = amount
        if payment_id:
            autopay.last_payment_id = payment_id
    session.flush()
    return autopay


def delete_autopay_method(session: Session, user_id: int) -> bool:
    autopay = get_autopay_method(session, user_id)
    if autopay is None:
        return False
    session.delete(autopay)
    session.flush()
    return True


def record_payment(
    session: Session,
    user_id: int,
    pay_metadata_id: int,
    payment_id: str,
    product: str | None,
    amount: int | None,
) -> PaymentRecord:
    record = session.execute(
        select(PaymentRecord).where(PaymentRecord.payment_id == payment_id)
    ).scalar()
    if record is None:
        record = PaymentRecord(
            user_id=user_id,
            pay_metadata_id=pay_metadata_id,
            payment_id=payment_id,
            product=product,
            amount=amount,
        )
        session.add(record)
        session.flush()
    return record


def get_last_subscription_payment_record(session: Session, user_id: int) -> PaymentRecord | None:
    return session.execute(
        select(PaymentRecord)
        .where(PaymentRecord.user_id == user_id)
        .where(PaymentRecord.product.ilike("subscribe%"))
        .order_by(PaymentRecord.created_at.desc())
    ).scalars().first()