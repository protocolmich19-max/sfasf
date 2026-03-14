from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, DeclarativeBase
from sqlalchemy import Column, Integer, String, create_engine, Boolean, BigInteger, select, Text, ForeignKey

from profit_utils import calculate_company_profit
import uvicorn
from threading import Thread
import time
import datetime
from telebot import TeleBot, types
from yookassa import Configuration, Payment
from contextlib import asynccontextmanager
import requests
import base64
import json
from decimal import Decimal, ROUND_HALF_UP
import uuid
import config
from db.connect import engine

# Инициализация бота и YooKassa из конфигурации
bot = TeleBot(config.TELEGRAM_BOT_TOKEN)
Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_API)

class Base(DeclarativeBase):
    created_at = Column(Integer, default=datetime.datetime.now(datetime.timezone.utc).timestamp())

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


class CompanyProfit(Base):
    __tablename__ = 'company_profits'

    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)


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


class EducationPayout(Base):
    __tablename__ = "education_payouts"

    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("education_purchases.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    payout_id = Column(String(255))
    status = Column(String(64))
    raw_response = Column(Text)
    error_message = Column(Text)

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

YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"
PAYOUT_DESCRIPTION_TEMPLATE = "Выплата партнёру за курс «{title}»"


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_education_product_id(product_code):
    if not isinstance(product_code, str):
        return None
    parts = product_code.split(":", 1)
    if len(parts) != 2 or parts[0] != "education":
        return None
    try:
        return int(parts[1])
    except (TypeError, ValueError):
        return None


def _parse_strategy_partner_product_id(product_code):
    if not isinstance(product_code, str):
        return None
    parts = product_code.split(":", 1)
    if len(parts) != 2 or parts[0] != "strategy_partner":
        return None
    try:
        return int(parts[1])
    except (TypeError, ValueError):
        return None


def _format_amount_rub(amount: int | float) -> str:
    decimal_amount = Decimal(amount).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    return f"{decimal_amount}"


def _ensure_partner_payout(
    session: Session,
    purchase: EducationPurchase,
    product: EducationProduct,
    user: User,
    amount_rub: int,
    wallet: str,
) -> dict[str, object]:
    existing = session.execute(
        select(EducationPayout).where(EducationPayout.purchase_id == purchase.id)
    ).scalar()
    if existing:
        return {
            "success": (existing.status == "succeeded" or existing.status == "pending"),
            "status": existing.status or "unknown",
            "error": existing.error_message,
        }

    amount_value = _format_amount_rub(amount_rub)
    description = PAYOUT_DESCRIPTION_TEMPLATE.format(title=product.title or product.slug or "курс")[:128]

    credentials = f"{SHOP_ID}:{SECRET_API}"
    auth_header = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4()),
        "Authorization": f"Basic {auth_header}",
    }
    payload = {
        "amount": {
            "value": amount_value,
            "currency": "RUB",
        },
        "payout_destination_data": {
            "type": "yoo_money",
            "account_number": wallet,
        },
        "description": description,
        "metadata": {
            "purchase_id": purchase.id,
            "product_id": product.id,
            "user_id": user.id,
        },
    }

    try:
        response = requests.post(
            f"{YOOKASSA_API_BASE}/payouts",
            headers=headers,
            json=payload,
            timeout=30,
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw": response.text}
    except Exception as exc:
        payout_record = EducationPayout(
            purchase_id=purchase.id,
            amount=amount_rub,
            status="error",
            error_message=str(exc),
        )
        session.add(payout_record)
        return {"success": False, "status": "error", "error": str(exc)}

    status_code = response.status_code
    status_text = None
    if isinstance(response_data, dict):
        status_text = response_data.get("status")
    if not status_text:
        status_text = f"HTTP {status_code}"

    success = status_code < 400 and status_text not in ("canceled", "error")
    error_message = None
    if not success:
        if isinstance(response_data, dict):
            error_message = response_data.get("description") or response_data.get("message")
        if not error_message:
            error_message = response.text

    payout_record = EducationPayout(
        purchase_id=purchase.id,
        amount=amount_rub,
        payout_id=response_data.get("id") if isinstance(response_data, dict) else None,
        status=status_text,
        raw_response=json.dumps(response_data, ensure_ascii=False, default=str) if response_data else None,
        error_message=error_message,
    )
    session.add(payout_record)

    return {
        "success": success,
        "status": status_text,
        "error": error_message,
    }


def process_strategy_partner_payment(session: Session, user: User, pay_metadata: PayMetadata, payment_id_value: str) -> bool:
    product_id = _parse_strategy_partner_product_id(pay_metadata.product)
    if product_id is None:
        return False

    product = session.get(StrategyPartnerProduct, product_id)
    if product is None:
        try:
            bot.send_message(
                ADMIN_ACCOUNT,
                f"[strategy_partner] Не найден продукт для оплаты #{pay_metadata.id} ({pay_metadata.product})",
            )
        except Exception:
            pass
        return True

    price_value = _to_int(pay_metadata.price) or _to_int(product.price) or 0
    partner_reward = product.partner_reward_amount or 0
    company_profit_percent = product.company_profit_percent or 0
    company_profit_amount = round(price_value * company_profit_percent / 100) if company_profit_percent else 0

    partner_user = None
    if getattr(product, "partner_user_id", None):
        partner_user = session.execute(select(User).where(User.id == product.partner_user_id)).scalar()

    partner_contact = product.owner_contact
    partner_tg_id = None
    partner_username = None
    if partner_user:
        partner_tg_id = partner_user.tg_id
        partner_username = partner_user.username
        partner_contact = partner_contact or (f"@{partner_username}" if partner_username else str(partner_user.tg_id))

    existing_purchase = session.execute(
        select(StrategyPartnerPurchase).where(StrategyPartnerPurchase.pay_metadata_id == pay_metadata.id)
    ).scalar()

    if existing_purchase is None:
        purchase = StrategyPartnerPurchase(
            product_id=product.id,
            user_id=user.id,
            pay_metadata_id=pay_metadata.id,
            payment_id=payment_id_value,
            amount=price_value,
            partner_reward_amount=partner_reward or None,
            company_profit_amount=company_profit_amount or None,
        )
        session.add(purchase)
        session.flush()
    else:
        purchase = existing_purchase
        purchase.amount = price_value
        purchase.partner_reward_amount = partner_reward or None
        purchase.company_profit_amount = company_profit_amount or None
        if payment_id_value:
            purchase.payment_id = payment_id_value

    if partner_tg_id:
        partner_lines = [
            f"🎉 Ваш продукт «{product.title}» купил @{user.username if user.username else user.tg_id}.",
            f"Сумма: {price_value} ₽",
        ]
        if partner_reward:
            partner_lines.append(f"Вознаграждение: {partner_reward} ₽")
        try:
            bot.send_message(partner_tg_id, "\n".join(partner_lines))
        except Exception:
            pass

    admin_lines = [
        f"Продукт стратегического партнёра «{product.title}» купил @{user.username if user.username else user.tg_id}.",
        f"Сумма: {price_value} ₽",
    ]
    if partner_reward:
        admin_lines.append(f"Вознаграждение партнёра: {partner_reward} ₽")
    if company_profit_percent:
        admin_lines.append(f"Прибыль компании ({company_profit_percent}%): {company_profit_amount} ₽")
    if payment_id_value:
        admin_lines.append(f"ID платежа: {payment_id_value}")

    admin_text = "\n".join(admin_lines)
    admin_kwargs = {"chat_id": ADMIN_CHAT_ID, "text": admin_text}
    if getattr(product, "notify_thread_id", None):
        admin_kwargs["message_thread_id"] = product.notify_thread_id
    try:
        bot.send_message(**admin_kwargs)
    except Exception:
        pass

    post_purchase_parts = []
    if product.post_purchase_message:
        post_purchase_parts.append(product.post_purchase_message)
    else:
        post_purchase_parts.append(f"Спасибо за покупку продукта «{product.title}»!")
    if product.post_purchase_link:
        post_purchase_parts.append(f"Материалы продукта: {product.post_purchase_link}")
    if partner_contact:
        post_purchase_parts.append(f"Свяжитесь с владельцем продукта: {partner_contact}")
    try:
        bot.send_message(user.tg_id, "\n\n".join(post_purchase_parts))
    except Exception:
        pass

    return True


def process_education_payment(session: Session, user: User, pay_metadata: PayMetadata, payment_id_value: str) -> bool:
    product_id = _parse_education_product_id(pay_metadata.product)
    if product_id is None:
        return False

    product = session.get(EducationProduct, product_id)
    if product is None:
        try:
            bot.send_message(
                ADMIN_ACCOUNT,
                f"[education] Не найден курс для оплаты #{pay_metadata.id} ({pay_metadata.product})",
            )
        except Exception:
            pass
        return True

    price_value = _to_int(pay_metadata.price) or _to_int(product.price) or 0
    partner_reward = product.partner_reward_amount or 0
    company_profit_percent = product.company_profit_percent or 0
    company_profit_amount = round(price_value * company_profit_percent / 100) if company_profit_percent else 0

    partner_user = None
    if getattr(product, "partner_user_id", None):
        partner_user = session.execute(select(User).where(User.id == product.partner_user_id)).scalar()

    partner_contact = product.owner_contact
    partner_tg_id = None
    partner_username = None
    if partner_user:
        partner_tg_id = partner_user.tg_id
        partner_username = partner_user.username
        partner_contact = partner_contact or (f"@{partner_username}" if partner_username else str(partner_user.tg_id))

    existing_purchase = session.execute(
        select(EducationPurchase).where(EducationPurchase.pay_metadata_id == pay_metadata.id)
    ).scalar()

    if existing_purchase is None:
        purchase = EducationPurchase(
            product_id=product.id,
            user_id=user.id,
            pay_metadata_id=pay_metadata.id,
            payment_id=payment_id_value,
            amount=price_value,
            partner_reward_amount=partner_reward or None,
            company_profit_amount=company_profit_amount or None,
        )
        session.add(purchase)
        session.flush()
    else:
        purchase = existing_purchase
        purchase.amount = price_value
        purchase.partner_reward_amount = partner_reward or None
        purchase.company_profit_amount = company_profit_amount or None
        if payment_id_value:
            purchase.payment_id = payment_id_value

    partner_wallet = (product.partner_account or "").strip()
    payout_result: dict[str, object] | None = None
    missing_wallet = bool(partner_reward and not partner_wallet)

    if partner_tg_id:
        partner_lines = [
            f"🎉 Ваш курс «{product.title}» купил @{user.username if user.username else user.tg_id}.",
            f"Сумма: {price_value} ₽",
        ]
        if partner_reward:
            partner_lines.append(f"Вознаграждение: {partner_reward} ₽")
        if payout_result:
            status_text = payout_result.get("status")
            if payout_result.get("success"):
                partner_lines.append(
                    f"💸 Перевод {partner_reward} ₽ на YooMoney кошелёк инициирован (статус: {status_text})."
                )
            else:
                error_text = payout_result.get("error")
                if error_text:
                    partner_lines.append(f"⚠️ Автовыплата не выполнена: {error_text}")
                else:
                    partner_lines.append("⚠️ Автовыплата не выполнена. Свяжитесь с администратором.")
        elif missing_wallet:
            partner_lines.append(
                "⚠️ Автовыплата не выполнена: для курса не указан кошелёк партнёра. Обратитесь к администратору."
            )
        try:
            bot.send_message(partner_tg_id, "\n".join(partner_lines))
        except Exception:
            pass

    admin_lines = [
        f"Образовательный курс «{product.title}» купил @{user.username if user.username else user.tg_id}.",
        f"Сумма: {price_value} ₽",
    ]
    if partner_reward:
        admin_lines.append(f"Вознаграждение партнёра: {partner_reward} ₽")
    if partner_wallet:
        admin_lines.append(f"Кошелёк партнёра: {partner_wallet}")
    if company_profit_percent:
        admin_lines.append(f"Прибыль компании ({company_profit_percent}%): {company_profit_amount} ₽")
    if payout_result:
        admin_lines.append(f"Статус выплаты партнёру: {payout_result.get('status')}")
        if payout_result.get("error"):
            admin_lines.append(f"Ошибка выплаты: {payout_result.get('error')}")
    elif missing_wallet:
        admin_lines.append("⚠️ Автовыплата не выполнена: не указан кошелёк партнёра.")
    if payment_id_value:
        admin_lines.append(f"ID платежа: {payment_id_value}")

    admin_text = "\n".join(admin_lines)
    admin_kwargs = {"chat_id": ADMIN_CHAT_ID, "text": admin_text}
    if getattr(product, "notify_thread_id", None):
        admin_kwargs["message_thread_id"] = product.notify_thread_id
    try:
        bot.send_message(**admin_kwargs)
    except Exception:
        pass

    post_purchase_parts = []
    if product.post_purchase_message:
        post_purchase_parts.append(product.post_purchase_message)
    else:
        post_purchase_parts.append(f"Спасибо за покупку курса «{product.title}»!")
    if product.post_purchase_link:
        post_purchase_parts.append(f"Материалы курса: {product.post_purchase_link}")
    if partner_contact:
        post_purchase_parts.append(f"Свяжитесь с владельцем курса: {partner_contact}")
    try:
        bot.send_message(user.tg_id, "\n\n".join(post_purchase_parts))
    except Exception:
        pass

    return True

def ref_handler(session: Session, user: User, pay_metadata: PayMetadata):
    # If the user has no ref, nothing to distribute
    if user.ref is None:
        session.commit()
        return
    user_ref = get_user_ref(session, user)
    admin_user = session.execute(select(User).where(User.id == 1)).scalar()
    total_pay_moneys = pay_metadata.price * (pay_metadata.procent_balance / 100)
    total_inner_pay_moneys = pay_metadata.price * (pay_metadata.inner_balance / 100)
    for i in range(1, 21):
        # Stop if there is no further ref in the chain
        if user_ref is None:
            break
        need_level = need_ref_level(i)
        pay_moneys = round(total_pay_moneys * get_ref_procent(i) / 100, 2)
        inner_pay_moneys = total_inner_pay_moneys * get_ref_inner_procent(i) / 100
        print(pay_moneys)
        if user_ref.ref_level >= need_level: 
            user_ref.balance += pay_moneys # начисление денег
            user_ref.inner_balance += inner_pay_moneys # начисление денег
            try:
                bot.send_message(user_ref.tg_id, f"""                   
Приглашенный вами пользователь @{user.username} купил продукт
Сумма: {pay_metadata.price} ₽
Вы получили: {pay_moneys} ₽""")
            except: pass
        else:
            admin_user.inner_balance += inner_pay_moneys # начисление денег
            admin_user.balance += pay_moneys
            try:
                bot.send_message(user_ref.tg_id, f"""
Вы упустили прибыль в {pay_moneys} ₽
Купите пакет {need_level} уровня, чтобы получать прибыль
                                """)
            except: pass
        print(i, user_ref.id)  
        user_ref = get_user_ref(session, user_ref)              
    session.commit()
def get_user_ref(session: Session, user: User):
    if user.ref == 1:
        return session.execute(select(User).where(User.id == user.ref)).scalar()
    return session.execute(select(User).where(User.tg_id == user.ref)).scalar()
def need_ref_level(line: int):
    if line == 1: return 1
    if line == 2 or line == 3: return 2
    if line == 4 or line == 5: return 3
    if line == 6 or line == 7: return 4
    if line == 8 or line == 9: return 5
    if line > 9: return 6
def get_ref_procent(line: int):
    if line == 1: return 40
    if line == 2: return 20
    if line == 3: return 14
    if line == 4: return 6
    if line == 5: return 6
    if line == 6: return 4
    if line == 7: return 4
    if line == 8: return 3
    if line == 9: return 2
    if line == 10: return 0.5
    if line == 11: return 0.25
    if line == 12: return 0.125 
    if line == 13: return 0.0625 
    if line == 14: return 0.03125 
    if line == 15: return 0.015625 
    if line == 16: return 0.0078125 
    if line == 17: return 0.00390625 
    if line == 18: return 0.001953125 
    if line == 19: return 0.0009765625 
    if line == 20: return 0.00048828125 
def get_ref_inner_procent(line: int):
    if line == 1: return 40
    if line == 2: return 40
    if line == 3: return 20
    else: return 0


def ensure_company_profit_record(session: Session, pay_metadata: PayMetadata):
    amount = calculate_company_profit(pay_metadata.product, pay_metadata.price)
    if amount is None and pay_metadata.product == "personalbot":
        amount = 3339
    if amount is None and pay_metadata.product == "servicecard":
        amount = 621
    if amount is None and pay_metadata.product == "pocketgame":
        amount = 2899
    if amount is None and isinstance(pay_metadata.product, str) and pay_metadata.product.startswith("education:"):
        product_id = _parse_education_product_id(pay_metadata.product)
        if product_id is not None:
            education_product = session.get(EducationProduct, product_id)
            if education_product is not None:
                price_value = _to_int(pay_metadata.price) or _to_int(education_product.price) or 0
                percent = education_product.company_profit_percent or 0
                amount = round(price_value * percent / 100) if percent else 0
    if amount is None and isinstance(pay_metadata.product, str) and pay_metadata.product.startswith("strategy_partner:"):
        product_id = _parse_strategy_partner_product_id(pay_metadata.product)
        if product_id is not None:
            strategy_partner_product = session.get(StrategyPartnerProduct, product_id)
            if strategy_partner_product is not None:
                price_value = _to_int(pay_metadata.price) or _to_int(strategy_partner_product.price) or 0
                percent = strategy_partner_product.company_profit_percent or 0
                amount = round(price_value * percent / 100) if percent else 0
    if amount is None:
        return
    existing = session.execute(
        select(CompanyProfit).where(CompanyProfit.payment_id == pay_metadata.id)
    ).scalar()
    if existing is not None:
        return
    if amount:
        session.add(CompanyProfit(payment_id=pay_metadata.id, amount=amount))

# Используем значения из конфигурации
ADMIN_ACCOUNT = config.ADMIN_ACCOUNT
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("[startup] starting checker background thread")
    except:
        pass
    thread = Thread(target=checker, daemon=True)
    thread.start()
    try:
        yield
    finally:
        try:
            print("[shutdown] app is shutting down")
        except:
            pass

app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)
try:
    EducationProduct.__table__.create(bind=engine, checkfirst=True)
    EducationPurchase.__table__.create(bind=engine, checkfirst=True)
    EducationPayout.__table__.create(bind=engine, checkfirst=True)
except Exception as exc:
    try:
        print(f"[checker] failed to ensure education tables: {exc}")
    except Exception:
        pass

try:
    StrategyPartnerProduct.__table__.create(bind=engine, checkfirst=True)
    StrategyPartnerPurchase.__table__.create(bind=engine, checkfirst=True)
except Exception as exc:
    try:
        print(f"[checker] failed to ensure strategy partner tables: {exc}")
    except Exception:
        pass

def checker():
    while True:
        with Session(engine) as session:
            try:
                payments = Payment.list({"limit": 100})
                for payment in payments.items:
                    try:
                        print(payment.id, payment.paid, getattr(payment, "amount", {}).value if getattr(payment, "amount", None) else None)
                        metadata = getattr(payment, "metadata", None) or {}
                        order_number = metadata.get("orderNumber") if isinstance(metadata, dict) else None
                        if not order_number or payment.paid is False:
                            continue
                        pay_metadata_id = int(order_number)
                        pay_metadata = session.execute(select(PayMetadata).where(PayMetadata.id == pay_metadata_id)).scalar()
                        if pay_metadata is None or pay_metadata.has_payed is True:
                            continue
                        user = session.execute(select(User).where(User.id == pay_metadata.user_id)).scalar()
                        if user is None:
                            # No user for metadata; mark as processed to avoid endless retries
                            pay_metadata.has_payed = True
                            session.commit()
                            continue

                        pay_metadata.has_payed = True

                        payment_id_value = getattr(payment, "id", None)
                        if payment_id_value:
                            existing_record = session.execute(
                                select(PaymentRecord).where(PaymentRecord.payment_id == payment_id_value)
                            ).scalar()
                            if existing_record is None:
                                session.add(
                                    PaymentRecord(
                                        user_id=user.id,
                                        pay_metadata_id=pay_metadata.id,
                                        payment_id=payment_id_value,
                                        product=pay_metadata.product,
                                        amount=_to_int(pay_metadata.price),
                                    )
                                )
                            autopay_entry = session.execute(
                                select(AutoPaymentMethod).where(AutoPaymentMethod.user_id == user.id)
                            ).scalar()
                            if autopay_entry:
                                autopay_entry.last_payment_id = payment_id_value
                                if isinstance(pay_metadata.product, str) and pay_metadata.product.lower().startswith("subscribe"):
                                    autopay_entry.product = pay_metadata.product
                                    autopay_entry.amount = _to_int(pay_metadata.price)

                        session.commit()

                        education_handled = process_education_payment(session, user, pay_metadata, payment_id_value)
                        if education_handled:
                            ensure_company_profit_record(session, pay_metadata)
                            ref_handler(session, user, pay_metadata)
                            session.commit()
                            continue

                        strategy_partner_handled = process_strategy_partner_payment(session, user, pay_metadata, payment_id_value)
                        if strategy_partner_handled:
                            ensure_company_profit_record(session, pay_metadata)
                            ref_handler(session, user, pay_metadata)
                            session.commit()
                            continue

                        if pay_metadata.product == "package":
                            if pay_metadata.price == 5000:
                                try: bot.send_message(user.tg_id, "Поздравляем, вы оплатили бизнес-пакет, вам активирован 2 и 3 уровень партнерской программы")
                                except: pass
                                user.ref_level = 2
                            if pay_metadata.price == 15000:
                                try: bot.send_message(user.tg_id, "Поздравляем, вы оплатили бизнес-пакет, вам активирован 4 и 5 уровень партнерской программы")
                                except: pass
                                user.ref_level = 3
                            if pay_metadata.price == 25000:
                                try: bot.send_message(user.tg_id, "Поздравляем, вы оплатили бизнес-пакет, вам активирован 6 и 7 уровень партнерской программы")
                                except: pass
                                user.ref_level = 4
                            if pay_metadata.price == 45000:
                                try: bot.send_message(user.tg_id, "Поздравляем, вы оплатили бизнес-пакет, вам активирован 8 и 9 уровень партнерской программы")
                                except: pass
                                user.ref_level = 5
                            if pay_metadata.price == 100000:
                                try: bot.send_message(user.tg_id, "Поздравляем, вы оплатили бизнес-пакет, вам активированы все 20 уровней партнерской программы")
                                except: pass
                                user.ref_level = 6
                            try: bot.send_message(ADMIN_CHAT_ID, f"Пользователь @{user.username} купил бизнес пакет за {pay_metadata.price} ₽", message_thread_id=8)
                            except: pass
                        if pay_metadata.product == "clubtraining":
                            user.ref_level = 5
                            try: bot.send_message(user.tg_id, "Вы оплатили обучающий курс «Организатор клуба знакомств».\n\nВам активирован подарок: подписка на 365 дней и 4 бизнес-пакета, которые открывают 2-9 уровень партнерской программы.")
                            except: pass
                            try: bot.send_message(user.tg_id, "Перейдите в канал «ГОСПОДА ВЕДУЩИЕ» и получите бесплатно обучение и онлайн поддержку:\n\nhttps://t.me/+1-Vj-ec0BOw1NTYy")
                            except: pass
                            try: bot.send_message(ADMIN_CHAT_ID, f'Пользователь @{user.username} купил игру за {pay_metadata.price} ₽. Дата: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', message_thread_id=3)
                            except: pass
                        if pay_metadata.product == "game":
                            try: bot.send_message(ADMIN_CHAT_ID, f'Пользователь @{user.username} купил игру на {pay_metadata.price} ₽. Дата: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', message_thread_id=3)
                            except: pass
                            try: bot.send_message(user.tg_id, "Поздравляем, вы приобрели комплект игры. Перейдите в канал «ГОСПОДА ВЕДУЩИЕ» и получите бесплатно обучение и онлайн поддержку:\n\nhttps://t.me/+1-Vj-ec0BOw1NTYy")
                            except: pass
                        try:
                            bot.send_message(ADMIN_ACCOUNT, f"""
        Пользователь @{user.username} купил {"подписку" if pay_metadata.product.startswith("subscribe") else "продукт"} на {pay_metadata.price} рублей
                                        """)
                        except: pass

                        if pay_metadata.product.startswith("subscribe"):
                            try: bot.send_message(ADMIN_CHAT_ID, f"Пользователь @{user.username} купил подписку на {pay_metadata.price} ₽", message_thread_id=2)
                            except: pass
                            try: bot.send_message(user.tg_id, "Для получения дальнейших инструкций обратитесь к @Forlove2025")
                            except: pass
                        elif pay_metadata.product.startswith("city_bot-"):
                            # Продление городского бота на 1 или 12 месяцев
                            try:
                                parts = str(pay_metadata.product).split("-")
                                months = int(parts[-1]) if parts and parts[-1].isdigit() else 0
                            except Exception:
                                months = 0
                            try: bot.send_message(user.tg_id, f"Оплата принята. Бот продлён на {months} мес.")
                            except: pass
                            try: bot.send_message(ADMIN_CHAT_ID, f"Городской бот продлён пользователем @{user.username} на {months} мес. Сумма: {pay_metadata.price} ₽", message_thread_id=2)
                            except: pass
                        elif pay_metadata.product == "personalbot":
                            try: bot.send_message(ADMIN_CHAT_ID, f"Пользователь @{user.username} оплатил личного бота ведущего за {pay_metadata.price} ₽", message_thread_id=2)
                            except: pass
                            try: bot.send_message(user.tg_id, """
💛 Поздравляем!
Вы только что сделали большой шаг к тому, чтобы ваш город, ваши встречи и ваше сообщество «За Любовь» стали ещё сильнее, живее и профессиональнее.

Осталось всего один шаг — создать бота . 
Вот подробная инструкция 👇

🔧 Инструкция по получению вашего бота

1. Зайти в @botFather
2. Написать ему команду /newbot
Придет сообщение: Alright, a new bot. How are we going to call it? Please choose a name for your bot.

3. Здесь пишем название вашего бота (любые слова на любом языке). Нажимаем "Отправить"
Придет сообщение: Good. Now let's choose a username for your bot. It must end in bot. Like this, for example: TetrisBot or tetris_bot.

4. После этого пишем ему username (тег. по которому его можно будет найти). Только на английском, заканчивается на bot, как в примере выше.

Если бот не отправил сообщение о том, что все создано, значит такой ник уже занят, либо не подходит под критерии.
Если бот успешно создан, придет длинное сообщение. Его нужно прислать @RodionRa

Если столкнулись с трудностями, также напишите аккаунту выше.
                            """)
                            except: pass
                        elif pay_metadata.product == "servicecard":
                            try: bot.send_message(user.tg_id, """
💛 Поздравляем вас с покупкой Сервисной карты “За Любовь”!

Вы сделали шаг в наше пространство заботы, выгод и красивых возможностей.
Теперь для вас открыта система привилегий, где средняя выгода по карте — от 100 000 ₽ 🌿

Свяжитесь , пожалуйста, с Артёмом @Forlove2025 , чтобы завершить оформление заказа .

Спасибо, что выбираете путь, где больше тепла, честности и любви. ✨
                            """)
                            except: pass
                            try: bot.send_message(ADMIN_CHAT_ID, f"Пользователь @{user.username} приобрёл сервисную карту за {pay_metadata.price} ₽", message_thread_id=2)
                            except: pass
                        elif pay_metadata.product == "pocketgame":
                            try: bot.send_message(ADMIN_CHAT_ID, f"Пользователь @{user.username} купил Карманную игру «За Любовь» за {pay_metadata.price} ₽", message_thread_id=3)
                            except: pass
                            try: bot.send_message(user.tg_id, """
💌 Поздравляем с покупкой Карманной игры “За Любовь”!

Вы выбрали маленькую коробочку, внутри которой — целая вселенная.

Это не просто мини-игра, а мощный и очень нежный инструмент, который помогает привлекать новых людей в систему «За Любовь».
Через один лёгкий, тёплый разговор человек соприкасается с ценностями проекта — и делает первый шаг глубже: к подписке, к большой игре, к партнёрству. ✨

А ещё для вашей пары - это инструмент, который помогает разговаривать по-настоящему: нежно, глубоко и без “как дела?”. Про чувства, про близость, про людей.

Совсем скоро с вами свяжется наша фея создания игр — Алёна.
Она уточнит все детали, оформит заказ и проведёт вас до самого получения игры 🌿

Спасибо, что выбираете «За Любовь».
                            """)
                            except: pass
                        elif pay_metadata.product != "package":
                            try: bot.send_message(user.tg_id, "Для получения дальнейших инструкций обратитесь к @Forlove2025")
                            except: pass
                        else:
                            try: bot.send_message(user.tg_id, "Увеличен заработок с реферальной программы")
                            except: pass

                        ensure_company_profit_record(session, pay_metadata)
                        ref_handler(session, user, pay_metadata)

                        session.commit()
                    except Exception as e:
                        # Log and continue with next payment
                        try:
                            print("Payment processing error:", e)
                        except:
                            pass
                        continue
                time.sleep(300)
            except Exception as e:
                try:
                    print("Checker loop error:", e)
                except:
                    pass
                # Shorter backoff to recover faster
                time.sleep(60)
   
   
  
@app.get("/")
def check_pay():
    return HTMLResponse("""
<h2>Перенаправление на бота</h2>
<script>window.open("https://t.me/forlove2025_bot", '_blank')</script>
""")

 