import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db.models import Base, User, PayMetadata
from handlers.subscription_checker import (
    has_active_subscription,
    get_subscription_days_left,
    format_subscription_remaining,
)


def _utc_ts(y, m, d):
    return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())


def setup_inmemory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


def _debug_dump(session, user_id: int, label: str):
    now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
    user = session.get(User, user_id)
    pays = session.execute(
        select(PayMetadata).where(PayMetadata.user_id == user_id).order_by(PayMetadata.created_at.asc())
    ).scalars().all()
    days_left = get_subscription_days_left(session, user_id)
    human = format_subscription_remaining(days_left)
    print(f"\n[DEBUG] {label}")
    print(f"now_utc_ts={now_ts}")
    print(f"user.created_at={getattr(user, 'created_at', None)}")
    for i, p in enumerate(pays, 1):
        print(
            f"pay#{i}: id={p.id} product={p.product} has_payed={p.has_payed} created_at={getattr(p, 'created_at', None)}"
        )
    print(f"days_left={days_left} -> {human}")


def test_grace_period_active():
    engine, Session = setup_inmemory()
    with Session() as s:
        # user created today -> within 30 days grace
        now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
        user = User(tg_id=1, username="u1", full_name="U1")
        user.created_at = now_ts
        s.add(user)
        s.commit()
        assert has_active_subscription(s, user.id) is True
        _debug_dump(s, user.id, "grace_period_active")


def test_grace_expired_no_payments():
    engine, Session = setup_inmemory()
    with Session() as s:
        user = User(tg_id=2, username="u2", full_name="U2")
        user.created_at = _utc_ts(2024, 1, 1)
        s.add(user)
        s.commit()
        assert has_active_subscription(s, user.id) is False
        _debug_dump(s, user.id, "grace_expired_no_payments")


def test_paid_subscribe_hyphen_1month():
    engine, Session = setup_inmemory()
    with Session() as s:
        now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
        # Grace expired to ensure paid path is used
        base_ts = now_ts - 60 * 86400
        user = User(tg_id=3, username="u3", full_name="U3")
        user.created_at = base_ts
        s.add(user)
        s.commit()

        # 1-month via hyphen
        pay = PayMetadata(user_id=user.id, product="subscribe-1", price=333, procent_balance=0, inner_balance=0)
        pay.has_payed = True
        # Purchased yesterday -> still active within 30 days
        pay.created_at = now_ts - 1 * 86400
        s.add(pay)
        s.commit()

        assert has_active_subscription(s, user.id) is True
        _debug_dump(s, user.id, "paid_subscribe_hyphen_1month")


def test_paid_subscribe_hyphen_12months():
    engine, Session = setup_inmemory()
    with Session() as s:
        now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
        # Grace expired long ago
        base_ts = now_ts - 400 * 86400
        user = User(tg_id=4, username="u4", full_name="U4")
        user.created_at = base_ts
        s.add(user)
        s.commit()

        pay = PayMetadata(user_id=user.id, product="subscribe-12", price=3333, procent_balance=0, inner_balance=0)
        pay.has_payed = True
        # Purchased 30 days ago -> still active for a year
        pay.created_at = now_ts - 30 * 86400
        s.add(pay)
        s.commit()

        assert has_active_subscription(s, user.id) is True
        _debug_dump(s, user.id, "paid_subscribe_hyphen_12months")


def test_stacking_multiple_payments():
    engine, Session = setup_inmemory()
    with Session() as s:
        user = User(tg_id=5, username="u5", full_name="U5")
        now_ts = int(dt.datetime.now(dt.timezone.utc).timestamp())
        # Grace long ago so only paid subs matter
        user.created_at = now_ts - 400 * 86400
        s.add(user)
        s.commit()

        # First: one month at (now - 50d) -> expiry (now - 20d)
        p1 = PayMetadata(user_id=user.id, product="subscribe-1", price=333, procent_balance=0, inner_balance=0)
        p1.has_payed = True
        p1.created_at = now_ts - 50 * 86400
        s.add(p1)

        # Second: one month at (now - 20d) -> stacks from previous expiry (now - 20d) => active until (now + 10d)
        p2 = PayMetadata(user_id=user.id, product="subscribe-1", price=333, procent_balance=0, inner_balance=0)
        p2.has_payed = True
        p2.created_at = now_ts - 20 * 86400
        s.add(p2)
        s.commit()

        assert has_active_subscription(s, user.id) is True
        _debug_dump(s, user.id, "stacking_multiple_payments")


