from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    Boolean,
    BigInteger,
    func,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase
import datetime
from db.connect import engine


class Base(DeclarativeBase):
    created_at = Column(
        Integer,
        default=lambda: int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    )


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger)
    username = Column(String(255))
    full_name = Column(String(255))
    phone = Column(String(255))
    city = Column(String(255))
    balance = Column(Integer, default=0)
    inner_balance = Column(Integer, default=0)
    has_ended = Column(Boolean, default=False)
    ref = Column(BigInteger)
    ref_level = Column(Integer, default=1)

class City(Base):
    __tablename__ = 'cities'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    text = Column(String(255))
    agent_account = Column(String(255))
    channel_link = Column(String(255))

class Schedule(Base):
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    city = Column(Integer)
    start = Column(String(255))

class PayMetadata(Base):
    __tablename__ = 'pay_metadatas'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    price = Column(Integer)
    product = Column(String(255))
    procent_balance = Column(Integer)
    inner_balance = Column(Integer)
    has_payed = Column(Boolean, default=False)

class BalanceTransfer(Base):
    __tablename__ = "balance_transafers"
    
    id = Column(Integer, primary_key=True)
    to_user_id = Column(Integer)
    from_user_id = Column(Integer)
    money = Column(Integer)
    
class Poster(Base):
    __tablename__ = "posters"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(128), index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    

class Promocode(Base):
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, index=True)
    has_activated = Column(Boolean, default=False)
    # created_at is inherited from Base as Integer (UTC timestamp)


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    pay_metadata_id = Column(Integer, index=True, nullable=False)
    payment_id = Column(String(255), unique=True, nullable=False)
    product = Column(String(255))
    amount = Column(Integer)


class AutoPaymentMethod(Base):
    __tablename__ = "auto_payment_methods"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    payment_method_id = Column(String(255), nullable=False)
    product = Column(String(255))
    amount = Column(Integer)
    last_payment_id = Column(String(255))
    last_attempt_at = Column(Integer)


class EducationProduct(Base):
    __tablename__ = "education_products"

    id = Column(Integer, primary_key=True)
    slug = Column(String(128), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    button_text = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    image = Column(String(512))
    video = Column(String(512))
    document = Column(String(512))
    partner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    partner_reward_amount = Column(Integer, nullable=False, default=0)
    partner_program_percent = Column(Integer, nullable=False, default=20)
    company_profit_percent = Column(Integer, nullable=False, default=20)
    partner_account = Column(String(255))
    owner_contact = Column(String(255))
    post_purchase_message = Column(Text)
    post_purchase_link = Column(String(512))
    notify_thread_id = Column(Integer)
    is_active = Column(Boolean, default=True)


class EducationPurchase(Base):
    __tablename__ = "education_purchases"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("education_products.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    pay_metadata_id = Column(Integer, nullable=False)
    payment_id = Column(String(255))
    amount = Column(Integer, nullable=False)
    partner_reward_amount = Column(Integer)
    company_profit_amount = Column(Integer)


class StrategyPartnerProduct(Base):
    __tablename__ = "strategy_partner_products"

    id = Column(Integer, primary_key=True)
    slug = Column(String(128), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    button_text = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    image = Column(String(512))
    video = Column(String(512))
    document = Column(String(512))
    partner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    partner_reward_amount = Column(Integer, nullable=False, default=0)
    partner_program_percent = Column(Integer, nullable=False, default=20)
    company_profit_percent = Column(Integer, nullable=False, default=20)
    partner_account = Column(String(255))
    owner_contact = Column(String(255))
    post_purchase_message = Column(Text)
    post_purchase_link = Column(String(512))
    notify_thread_id = Column(Integer)
    is_active = Column(Boolean, default=True)


class StrategyPartnerPurchase(Base):
    __tablename__ = "strategy_partner_purchases"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("strategy_partner_products.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    pay_metadata_id = Column(Integer, nullable=False)
    payment_id = Column(String(255))
    amount = Column(Integer, nullable=False)
    partner_reward_amount = Column(Integer)
    company_profit_amount = Column(Integer)


def init_db():
    Base.metadata.create_all(engine)