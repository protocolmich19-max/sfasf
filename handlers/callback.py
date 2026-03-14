from sqlalchemy import select
from telebot import TeleBot, types
from sqlalchemy.orm import Session
from db.connect import engine
from db.models import (
    BalanceTransfer,
    City,
    PayMetadata,
    Schedule,
    User,
    Poster,
    EducationProduct,
    StrategyPartnerProduct,
)
from db.handlers import (
    delete_autopay_method,
    get_autopay_method,
    get_last_subscription_payment_record,
    upsert_autopay_method,
)
from datetime import datetime
from handlers.handler import get_list_refs, get_user_ref
from yookassa import Configuration, Payment
import uuid
import html
import os

from handlers.start import handle_start_message
from handlers.subscription_checker import get_subscription_days_left, format_subscription_remaining
import config

# Инициализация YooKassa из конфигурации
Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_API)

# Используем значения из конфигурации
ADMIN_ACCOUNT = config.ADMIN_ACCOUNT
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID
ADMIN_EDUCATION_THREAD_ID = config.ADMIN_EDUCATION_THREAD_ID

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EDUCATION_CONTENT_TEXT = (
    "Образовательный контент — это витрина авторских курсов проекта «За любовь». "
    "Скоро здесь появятся полноценные программы с поддержкой наставников, готовыми "
    "для покупки прямо в боте. Пока дизайнер готовит финальные медиа, используем "
    "моковые материалы, чтобы отладить сценарии."
)
EDUCATION_CONTENT_IMAGE = "assets/subscribe-img.png"
EDUCATION_CONTENT_IMAGE_CAPTION = "Превью образовательных программ (мок)."
EDUCATION_CONTENT_VIDEO = "assets/video_tour.mp4"
EDUCATION_CONTENT_VIDEO_CAPTION = "Видео-презентация раздела (мок)."
EDUCATION_CONTENT_DOCUMENT = "assets/company_medias/За любовь презентация.pdf"
EDUCATION_CONTENT_DOCUMENT_CAPTION = "PDF-презентация проекта (мок)."
EDUCATION_PURCHASE_INTRO = (
    "После оплаты мы пришлём инструкции и материал курса в этом же чате."
)
EDUCATION_EXPERT_PROMPT = (
    "Расскажите, какие программы хотите создать, опыт и чем будете полезны. "
    "Мы передадим заявку куратору образовательного направления."
)

STRATEGY_PARTNERS_TEXT = (
    "Стратегические партнеры — это специальные продукты и услуги от наших партнёров. "
    "Здесь вы найдёте эксклюзивные предложения, которые помогут вам в развитии и бизнесе."
)
STRATEGY_PARTNERS_IMAGE = "assets/subscribe-img.png"
STRATEGY_PARTNERS_IMAGE_CAPTION = "Превью продуктов стратегических партнёров."
STRATEGY_PARTNERS_VIDEO = "assets/video_tour.mp4"
STRATEGY_PARTNERS_VIDEO_CAPTION = "Видео-презентация раздела."
STRATEGY_PARTNERS_DOCUMENT = "assets/company_medias/За любовь презентация.pdf"
STRATEGY_PARTNERS_DOCUMENT_CAPTION = "PDF-презентация проекта."
STRATEGY_PARTNERS_PURCHASE_INTRO = (
    "После оплаты мы пришлём инструкции и материалы продукта в этом же чате."
)
STRATEGY_PARTNERS_EXPERT_PROMPT = (
    "Расскажите, какие продукты или услуги хотите предложить, ваш опыт и чем будете полезны. "
    "Мы передадим заявку куратору направления стратегических партнёров."
)


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_autopay(session: Session, user_id: int) -> bool:
    return get_autopay_method(session, user_id) is not None


def _append_autopay_button(
    markup: types.InlineKeyboardMarkup,
    has_autopay: bool,
) -> types.InlineKeyboardMarkup:
    button_text = "Отключить автоплатеж" if has_autopay else "Подключить автоплатеж"
    callback_data = "subscribe-autopay-disable" if has_autopay else "subscribe-autopay-enable"
    markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    return markup


def _send_media(bot: TeleBot, chat_id: int, media_path: str, sender, **kwargs):
    if not media_path:
        return
    if isinstance(media_path, str) and media_path.startswith(("http://", "https://")):
        try:
            sender(chat_id, media_path, **kwargs)
        except Exception as exc:
            try:
                print(f"[education] failed to send remote media {media_path}: {exc}")
            except Exception:
                pass
        return
    full_path = media_path
    if isinstance(media_path, str) and not os.path.isabs(media_path):
        full_path = os.path.normpath(os.path.join(PROJECT_ROOT, media_path))
    try:
        with open(full_path, "rb") as media_file:
            sender(chat_id, media_file, **kwargs)
    except FileNotFoundError:
        try:
            print(f"[education] media file not found: {full_path}")
        except Exception:
            pass
    except Exception as exc:
        try:
            print(f"[education] failed to send media {full_path}: {exc}")
        except Exception:
            pass


from typing import Optional


def _escape(text: Optional[str]) -> str:
    return html.escape(text or "")


def _format_user(user: Optional[User], fallback_tg_id: Optional[int] = None) -> str:
    if user and user.username:
        return f"@{user.username}"
    if fallback_tg_id:
        return f"id {fallback_tg_id}"
    if user and user.tg_id:
        return f"id {user.tg_id}"
    return "пользователь"


def _send_education_overview(bot: TeleBot, chat_id: int) -> None:
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Каталог курсов", callback_data="education_catalog"),
        types.InlineKeyboardButton("Стать экспертом", callback_data="education_become_expert"),
        row_width=1,
    )
    bot.send_message(chat_id, EDUCATION_CONTENT_TEXT, reply_markup=markup)
    _send_media(bot, chat_id, EDUCATION_CONTENT_IMAGE, bot.send_photo, caption=EDUCATION_CONTENT_IMAGE_CAPTION)
    _send_media(bot, chat_id, EDUCATION_CONTENT_VIDEO, bot.send_video, caption=EDUCATION_CONTENT_VIDEO_CAPTION)
    _send_media(
        bot,
        chat_id,
        EDUCATION_CONTENT_DOCUMENT,
        bot.send_document,
        caption=EDUCATION_CONTENT_DOCUMENT_CAPTION,
    )


def _send_strategy_partners_overview(bot: TeleBot, chat_id: int) -> None:
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Каталог продуктов", callback_data="strategy_partners_catalog"),
        types.InlineKeyboardButton("Стать партнёром", callback_data="strategy_partners_become_partner"),
        row_width=1,
    )
    bot.send_message(chat_id, STRATEGY_PARTNERS_TEXT, reply_markup=markup)
    _send_media(bot, chat_id, STRATEGY_PARTNERS_IMAGE, bot.send_photo, caption=STRATEGY_PARTNERS_IMAGE_CAPTION)
    _send_media(bot, chat_id, STRATEGY_PARTNERS_VIDEO, bot.send_video, caption=STRATEGY_PARTNERS_VIDEO_CAPTION)
    _send_media(
        bot,
        chat_id,
        STRATEGY_PARTNERS_DOCUMENT,
        bot.send_document,
        caption=STRATEGY_PARTNERS_DOCUMENT_CAPTION,
    )


def _send_education_catalog(bot: TeleBot, chat_id: int, session: Session) -> None:
    products = session.execute(
        select(EducationProduct).where(EducationProduct.is_active == True)  # noqa: E712
    ).scalars().all()
    markup = types.InlineKeyboardMarkup()
    if products:
        for product in products:
            button_title = product.button_text or product.title
            markup.add(types.InlineKeyboardButton(button_title, callback_data=f"education_course:{product.id}"))
        text = "Выберите курс, чтобы посмотреть описание и материалы."
    else:
        text = "Каталог курсов появится в ближайшее время."
    markup.add(types.InlineKeyboardButton("⬅️ Обзор раздела", callback_data="education_content"))
    bot.send_message(chat_id, text, reply_markup=markup)


def _send_strategy_partners_catalog(bot: TeleBot, chat_id: int, session: Session) -> None:
    products = session.execute(
        select(StrategyPartnerProduct).where(StrategyPartnerProduct.is_active == True)  # noqa: E712
    ).scalars().all()
    markup = types.InlineKeyboardMarkup()
    if products:
        for product in products:
            button_title = product.button_text or product.title
            markup.add(types.InlineKeyboardButton(button_title, callback_data=f"strategy_partners_product:{product.id}"))
        text = "Выберите продукт, чтобы посмотреть описание и материалы."
    else:
        text = "Каталог продуктов появится в ближайшее время."
    markup.add(types.InlineKeyboardButton("⬅️ Обзор раздела", callback_data="strategy_partners_content"))
    bot.send_message(chat_id, text, reply_markup=markup)


def _send_education_product(
    bot: TeleBot,
    chat_id: int,
    session: Session,
    product_id: int,
) -> None:
    product = session.get(EducationProduct, product_id)
    if not product or not product.is_active:
        bot.send_message(chat_id, "Курс временно недоступен.")
        return

    _send_media(
        bot,
        chat_id,
        product.image,
        bot.send_photo,
        caption=product.title if product.title else None,
    )
    _send_media(
        bot,
        chat_id,
        product.video,
        bot.send_video,
        caption=f"{product.title} — видео-презентация" if product.title else None,
    )
    _send_media(
        bot,
        chat_id,
        product.document,
        bot.send_document,
        caption=f"{product.title} — презентация" if product.title else None,
    )

    description_html = _escape(product.description)
    lines = [
        f"<b>{_escape(product.title)}</b>" if product.title else None,
        description_html,
        f"<b>Стоимость:</b> {product.price} ₽" if product.price is not None else None,
        f"<b>Контакт владельца:</b> {_escape(product.owner_contact)}" if product.owner_contact else None,
    ]
    message_text = "\n\n".join(filter(None, lines))
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Приобрести", callback_data=f"education_purchase:{product.id}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад к каталогу", callback_data="education_catalog"))
    bot.send_message(chat_id, message_text, parse_mode="HTML", reply_markup=markup)


def _send_strategy_partners_product(
    bot: TeleBot,
    chat_id: int,
    session: Session,
    product_id: int,
) -> None:
    product = session.get(StrategyPartnerProduct, product_id)
    if not product or not product.is_active:
        bot.send_message(chat_id, "Продукт временно недоступен.")
        return

    _send_media(
        bot,
        chat_id,
        product.image,
        bot.send_photo,
        caption=product.title if product.title else None,
    )
    _send_media(
        bot,
        chat_id,
        product.video,
        bot.send_video,
        caption=f"{product.title} — видео-презентация" if product.title else None,
    )
    _send_media(
        bot,
        chat_id,
        product.document,
        bot.send_document,
        caption=f"{product.title} — презентация" if product.title else None,
    )

    description_html = _escape(product.description)
    lines = [
        f"<b>{_escape(product.title)}</b>" if product.title else None,
        description_html,
        f"<b>Стоимость:</b> {product.price} ₽" if product.price is not None else None,
        f"<b>Контакт владельца:</b> {_escape(product.owner_contact)}" if product.owner_contact else None,
    ]
    message_text = "\n\n".join(filter(None, lines))
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Приобрести", callback_data=f"strategy_partners_purchase:{product.id}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад к каталогу", callback_data="strategy_partners_catalog"))
    bot.send_message(chat_id, message_text, parse_mode="HTML", reply_markup=markup)


def _start_education_purchase(
    bot: TeleBot,
    chat_id: int,
    session: Session,
    user: User,
    product_id: int,
) -> None:
    product = session.get(EducationProduct, product_id)
    if not product or not product.is_active:
        bot.send_message(chat_id, "Курс временно недоступен.")
        return

    price = _safe_int(product.price)
    if price is None or price <= 0:
        bot.send_message(chat_id, "Для курса не указана корректная стоимость.")
        return

    procent_balance = product.partner_program_percent or 0

    pay_metadata = PayMetadata(
        user_id=user.id,
        price=price,
        product=f"education:{product.id}",
        procent_balance=procent_balance,
        inner_balance=0,
    )
    session.add(pay_metadata)
    session.commit()

    idempotence_key = str(uuid.uuid4())
    amount_value = f"{price}"
    item_description = (product.title or "Образовательный курс")[:128]

    payment = Payment.create(
        {
            "id": idempotence_key,
            "amount": {
                "value": amount_value,
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/forlove2025_bot",
            },
            "capture": True,
            "description": str(pay_metadata.id),
            "metadata": {
                "orderNumber": pay_metadata.id,
            },
            "receipt": {
                "customer": {
                    "full_name": "Николаев Артем Алексеевич",
                    "email": "cfznyjdf13@mail.ru",
                    "phone": "79166758299",
                    "inn": "170108382176",
                },
                "items": [
                    {
                        "description": item_description,
                        "quantity": "1.00",
                        "amount": {
                            "value": amount_value,
                            "currency": "RUB",
                        },
                        "vat_code": "2",
                        "payment_mode": "full_payment",
                        "payment_subject": "commodity",
                    },
                ],
            },
        },
        idempotency_key=idempotence_key,
    )

    confirmation_url = payment.confirmation.confirmation_url
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Оплатить {price} ₽", url=confirmation_url))
    markup.add(types.InlineKeyboardButton("⬅️ Назад к описанию", callback_data=f"education_course:{product.id}"))

    text_lines = [
        f"Курс: {product.title}",
        f"Стоимость: {price} ₽",
        "",
        EDUCATION_PURCHASE_INTRO,
    ]
    bot.send_message(chat_id, "\n".join(filter(None, text_lines)), reply_markup=markup)


def _start_strategy_partners_purchase(
    bot: TeleBot,
    chat_id: int,
    session: Session,
    user: User,
    product_id: int,
) -> None:
    product = session.get(StrategyPartnerProduct, product_id)
    if not product or not product.is_active:
        bot.send_message(chat_id, "Продукт временно недоступен.")
        return

    price = _safe_int(product.price)
    if price is None or price <= 0:
        bot.send_message(chat_id, "Для продукта не указана корректная стоимость.")
        return

    procent_balance = product.partner_program_percent or 0

    pay_metadata = PayMetadata(
        user_id=user.id,
        price=price,
        product=f"strategy_partner:{product.id}",
        procent_balance=procent_balance,
        inner_balance=0,
    )
    session.add(pay_metadata)
    session.commit()

    idempotence_key = str(uuid.uuid4())
    amount_value = f"{price}"
    item_description = (product.title or "Продукт стратегического партнёра")[:128]

    payment = Payment.create(
        {
            "id": idempotence_key,
            "amount": {
                "value": amount_value,
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/forlove2025_bot",
            },
            "capture": True,
            "description": str(pay_metadata.id),
            "metadata": {
                "orderNumber": pay_metadata.id,
            },
            "receipt": {
                "customer": {
                    "full_name": "Николаев Артем Алексеевич",
                    "email": "cfznyjdf13@mail.ru",
                    "phone": "79166758299",
                    "inn": "170108382176",
                },
                "items": [
                    {
                        "description": item_description,
                        "quantity": "1.00",
                        "amount": {
                            "value": amount_value,
                            "currency": "RUB",
                        },
                        "vat_code": "2",
                        "payment_mode": "full_payment",
                        "payment_subject": "commodity",
                    },
                ],
            },
        },
        idempotency_key=idempotence_key,
    )

    confirmation_url = payment.confirmation.confirmation_url
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Оплатить {price} ₽", url=confirmation_url))
    markup.add(types.InlineKeyboardButton("⬅️ Назад к описанию", callback_data=f"strategy_partners_product:{product.id}"))

    text_lines = [
        f"Продукт: {product.title}",
        f"Стоимость: {price} ₽",
        "",
        STRATEGY_PARTNERS_PURCHASE_INTRO,
    ]
    bot.send_message(chat_id, "\n".join(filter(None, text_lines)), reply_markup=markup)


def _start_education_expert_flow(bot: TeleBot, call: types.CallbackQuery) -> None:
    bot.send_message(
        call.from_user.id,
        f"{EDUCATION_EXPERT_PROMPT}\n\nОтправьте информацию одним сообщением. Чтобы выйти, нажмите «На главную».",
    )
    bot.register_next_step_handler(call.message, _education_expert_submit, bot)


def _start_strategy_partners_flow(bot: TeleBot, call: types.CallbackQuery) -> None:
    bot.send_message(
        call.from_user.id,
        f"{STRATEGY_PARTNERS_EXPERT_PROMPT}\n\nОтправьте информацию одним сообщением. Чтобы выйти, нажмите «На главную».",
    )
    bot.register_next_step_handler(call.message, _strategy_partners_submit, bot)


def handler_callback(bot: TeleBot, call: types.CallbackQuery):
    with Session(engine) as session:
        user = session.execute(select(User).where(User.tg_id == call.from_user.id)).scalar() # call.from_user.id
        
        if call.data == "about_project":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Наши города",callback_data="our_cities") 
            markup.add(button)
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/C1BkGvK1/photo-2025-08-20-14-14-21.jpg", caption="""        
Проект 'За любовь' — это уникальная экосистема, созданная для тех, кто хочет строить крепкие и осознанные отношения, развиваться как личность и быть частью большого сообщества единомышленников. Мы верим, что любовь, уважение и верность — это основа счастливой жизни. 

Наши инструменты — это увлекательные настольные игры, образовательные курсы, оффлайн-клубы знакомств, фестивали и партнерская программа, которая позволяет зарабатывать, делясь нашими ценностями. Узнайте больше о том, как мы помогаем людям находить гармонию и вдохновение!

Присоединяйтесь к движению, которое меняет жизни к лучшему!

https://rutube.ru/video/3641a629d7c72c037332444530a1636b/?r=a/
    """, reply_markup=markup)
            f = open('assets/Презентация о проекте.pdf', 'rb')
            bot.send_document(call.from_user.id, f)
        elif call.data == 'media_channels':
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Telegram канал", url="https://t.me/za_lyubov_igra")
            button2 = types.InlineKeyboardButton("Rutube", url="https://rutube.ru/channel/25861872")
            button3 = types.InlineKeyboardButton("Презентации компании", callback_data="company_media")
            markup.add(button, button2, button3, row_width=1)
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/Bv0mCY7M/photo-2025-08-20-16-21-57.jpg", """        
Будьте в курсе всех новостей и событий проекта 'За любовь'! 

Подписывайтесь на наши социальные сети, чтобы следить за анонсами мероприятий, вдохновляющими историями участников и полезными материалами. 
Мы делимся видео, статьями и отзывами, чтобы вы чувствовали себя частью нашего сообщества!
    """, reply_markup=markup)
        elif call.data == "company_media":
            bot.send_document(call.message.chat.id, open("assets/company_medias/За любовь презентация.pdf", 'rb'), caption="Презентация. Общая\n\nhttps://rutube.ru/video/3641a629d7c72c037332444530a1636b/?r=a/")
            bot.send_document(call.message.chat.id, open("assets/company_medias/Социальный_предприниматель_1_06_2025.pptx", 'rb'), caption="Презентация Социальный предприниматель\n\nhttps://rutube.ru/video/651413f1de8d4238e9e8fad6d5d13189/?r=a/")
            bot.send_document(call.message.chat.id, open("assets/company_medias/Клуб знакомств.pptx", 'rb'), caption="Организатор клуба знакомств\n\nhttps://rutube.ru/video/408550ceccd2c78daf0594ffd0b99ae0/?r=a/")
            bot.send_document(call.message.chat.id, open("assets/company_medias/ПартнеркаЗаЛюбовь.pdf", 'rb'), caption="Партнеская программа\n\nhttps://rutube.ru/video/4a15e34316ff713ed345842df1134729/?r=a/")
            bot.send_document(call.message.chat.id, open("assets/company_medias/Сертификат За Любовь.pptx", 'rb'), caption="ПОДАРОЧНЫЙ СЕРТИФИКАТ За любовь\n\nhttps://rutube.ru/video/707d181398de541a82184a5d08eacb3e/?r=a/")
        elif call.data == "education_content":
            _send_education_overview(bot, call.from_user.id)
        elif call.data == "education_catalog":
            _send_education_catalog(bot, call.from_user.id, session)
        elif call.data.startswith("education_course:"):
            try:
                product_id = int(call.data.split(":")[1])
            except (IndexError, ValueError):
                bot.send_message(call.from_user.id, "Курс не найден.")
            else:
                _send_education_product(bot, call.from_user.id, session, product_id)
        elif call.data.startswith("education_purchase:"):
            if user is None:
                bot.send_message(call.from_user.id, "Сначала зарегистрируйтесь в боте.")
            else:
                try:
                    product_id = int(call.data.split(":")[1])
                except (IndexError, ValueError):
                    bot.send_message(call.from_user.id, "Курс не найден.")
                else:
                    _start_education_purchase(bot, call.from_user.id, session, user, product_id)
        elif call.data == "education_become_expert":
            _start_education_expert_flow(bot, call)
        
        # СТРАТЕГИЧЕСКИЕ ПАРТНЕРЫ
        elif call.data == "strategy_partners_content":
            _send_strategy_partners_overview(bot, call.from_user.id)
        elif call.data == "strategy_partners_catalog":
            _send_strategy_partners_catalog(bot, call.from_user.id, session)
        elif call.data.startswith("strategy_partners_product:"):
            try:
                product_id = int(call.data.split(":")[1])
            except (IndexError, ValueError):
                bot.send_message(call.from_user.id, "Продукт не найден.")
            else:
                _send_strategy_partners_product(bot, call.from_user.id, session, product_id)
        elif call.data.startswith("strategy_partners_purchase:"):
            if user is None:
                bot.send_message(call.from_user.id, "Сначала зарегистрируйтесь в боте.")
            else:
                try:
                    product_id = int(call.data.split(":")[1])
                except (IndexError, ValueError):
                    bot.send_message(call.from_user.id, "Продукт не найден.")
                else:
                    _start_strategy_partners_purchase(bot, call.from_user.id, session, user, product_id)
        elif call.data == "strategy_partners_become_partner":
            _start_strategy_partners_flow(bot, call)
        
        # ГОРОДА
        elif call.data == "sign_for_game":
            markup = types.InlineKeyboardMarkup()
            button1 = types.InlineKeyboardButton("Об игре",callback_data="about_game")
            button2 = types.InlineKeyboardButton("Наши города",callback_data="our_cities") 
            markup.add(button1, button2, row_width=1)
            bot.send_photo(call.from_user.id,"https://i.postimg.cc/rFnyTqJB/photo-2025-08-20-14-17-43.jpg", "Настольная игра 'За любовь' — это не просто развлечение, а уникальный способ познакомиться с новыми людьми, укрепить связи и обсудить важные жизненные темы в легкой и непринужденной атмосфере.\n\nИгра подходит для всех — от друзей до семейных пар. Запишитесь на ближайшее мероприятие в вашем городе и откройте для себя мир осознанного общения!\n\nhttps://rutube.ru/video/4e9613850ede65b96a1560b214d78851/?r=a/", reply_markup=markup)
        elif call.data == "about_game":
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/Dz3mfm2p/photo-2025-08-19-14-16-58.jpg", caption="""
Игра 'За любовь' создана для 1–12 участников и подходит для людей любого возраста, которые хотят лучше понять себя и других. 

В комплект входят карточки с глубокими вопросами, заданиями и сценариями, которые помогают раскрыться, обсудить ценности и выстроить доверие. 
Это идеальный способ начать свое путешествие в экосистеме 'За любовь'. Узнайте, как игра может изменить ваш взгляд на отношения!

Нажмите кнопку "Наши города", чтобы узнать, где есть наши представительства и организуются игры.

https://rutube.ru/video/9c75b2a7c4fca023f392041b837e8fec/?r=a/""")
        elif call.data == "our_cities":
            cities = session.execute(select(City)).scalars().all()
            markup = types.InlineKeyboardMarkup()
            for city in cities:
                button = types.InlineKeyboardButton(city.name, callback_data=f"_city_{city.id}")
                markup.add(button)
            video = open('assets/our_cities.mp4', 'rb')
            bot.send_video(call.from_user.id, video, timeout=20, caption="Мы уже работаем в 12 городах России, и наша сеть растет!\n\nВыберите свой город, чтобы узнать о ближайших играх, познакомиться с организатором и присоединиться к местному сообществу 'За любовь'", reply_markup=markup)
        elif call.data.startswith("_city_"):
            city_id = int(call.data.split("_")[2])
            city = session.execute(select(City).where(City.id == city_id)).scalar()
            if city != None:
                posters = session.execute(select(Poster).where(Poster.city == city.name)).scalars().all()
                if len(posters) > 0:
                    for poster in posters:
                        if poster.image_url:
                            bot.send_photo(call.from_user.id, poster.image_url, caption=poster.description if poster.description else None)
                        elif poster.description:
                            bot.send_message(call.from_user.id, poster.description)
        
        
        # ПОДПИСКА
        elif call.data == "subscribe":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("На месяц за 333 ₽", callback_data=f"buy-subscribe_1_333")
            button2 = types.InlineKeyboardButton("На год за 3333 ₽", callback_data=f"buy-subscribe_12_3333")
            markup.add(button,button2, row_width=1)
            _append_autopay_button(markup, _has_autopay(session, user.id) if user else False)
            video = open("assets/subscribe.mp4", 'rb')
            bot.send_video(call.from_user.id, video, duration=10, caption="""
Подписка 'За любовь' — это ваш ключ к полной экосистеме проекта! За 333 руб./мес. (первый месяц бесплатно) вы получаете доступ к эксклюзивным образовательным курсам по психологии отношений, эмоциональному интеллекту и личностному росту, а также к маркетплейсу, партнерской программе и закрытым мероприятиям. 

Это ваш шанс учиться, общаться и зарабатывать в одном месте. Также вы сможете начать зарабатывать по партнерской программе.

Оформите подписку и начните свое путешествие к гармонии

https://rutube.ru/video/3641a629d7c72c037332444530a1636b/?r=a/""", reply_markup=markup)
        elif call.data.startswith("buy-subscribe"):
            # реализовать создание платежа
            pay_link = 'https://example.com'
            months = call.data.split("_")[1]
            price = call.data.split("_")[2]
            
            pay_metadata = PayMetadata(
            user_id = user.id, 
                price = price,
                product = f"subscribe-{months}",
                procent_balance = 50,
                inner_balance = 0
            )
            
            session.add(pay_metadata)
            session.commit()
            
            idempotence_key = str(uuid.uuid4())
            
            payment = Payment.create(
                {
                    "id": idempotence_key,
                    "amount": {
                        "value": price,
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": "https://t.me/forlove2025_bot"
                    },
                    "capture": True,
                    "description": pay_metadata.id,
                    "metadata": {
                        'orderNumber': pay_metadata.id
                    },
                    "receipt": {
                        "customer": {
                            "full_name": "Николаев Артем Алексеевич",
                            "email": "cfznyjdf13@mail.ru",
                            "phone": "79166758299",
                            "inn": "170108382176"
                        },
                        "items": [
                            {
                                "description": "Подписка платформы",
                                "quantity": "1.00",
                                "amount": {
                                    "value": price,
                                    "currency": "RUB"
                                },
                                "vat_code": "2",
                                "payment_mode": "full_payment",
                                "payment_subject": "commodity",
                                "country_of_origin_code": "RU",
                                "product_code": "44 4D 01 00 21 FA 41 00 23 05 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 12 00 AB 00",
                                "customs_declaration_number": "10714040/140917/0090376",
                                "excise": "20.00",
                                "supplier": {
                                    "name": "string",
                                    "phone": "string",
                                    "inn": "string"
                                }
                            },
                        ]
                    },
                }, 
                idempotency_key=idempotence_key
            )
            

            # get confirmation url
            confirmation_url = payment.confirmation.confirmation_url
            
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(f"Оплатить ({price} ₽)", url=confirmation_url)
            #button2 = types.InlineKeyboardButton(f"Проверить оплату", callback_data=f"check-buy-subscribe_{pay_metadata.id}")
            markup.add(button, row_width=1)
            _append_autopay_button(markup, _has_autopay(session, user.id) if user else False)
            
            
            bot.send_photo(call.from_user.id, "https://s3.iimg.su/s/15/g3fqZ2AxMZ1uyqVv8WglGq923WJdcXeoMNCrSzlJ.png", caption=f"""
Благодарим за подписку. У вас активирован статус личная активность в течении 30 суток. Для получения бонусов партнерской программы и бонусных материалов платформы (По окончанию оплаченного срока действия подписки все модули будут автоматически отключены. Рекомендуем оплатить подписку на 12 месяцев со скидкой стоимостью 3333 рубля)

https://rutube.ru/video/d2cd0a333593fb53f878f54e01829c4e/?r=a/
                             """, reply_markup=markup)
        elif call.data == "subscribe-autopay-enable":
            if user is None:
                try:
                    bot.answer_callback_query(call.id, "Пользователь не найден")
                except:
                    pass
                return
            if _has_autopay(session, user.id):
                try:
                    bot.answer_callback_query(call.id, "Автоплатеж уже подключён")
                except:
                    pass
                return
            payment_record = get_last_subscription_payment_record(session, user.id)
            if payment_record is None:
                text = "Не нашли успешных оплат подписки. Сначала оплатите подписку обычным способом."
                bot.send_message(call.from_user.id, text)
                return
            try:
                response = Payment.find(payment_record.payment_id)
            except Exception as exc:
                session.rollback()
                bot.send_message(call.from_user.id, f"Не удалось получить данные оплаты: {exc}")
                return

            status = str(getattr(response, "status", "")).lower()
            paid_flag = getattr(response, "paid", None)
            if status != "succeeded" and paid_flag is not True:
                bot.send_message(
                    call.from_user.id,
                    "Последняя оплата ещё не завершена. Попробуйте подключить автоплатёж позже.",
                )
                return

            payment_method = getattr(response, "payment_method", None)
            method_id = getattr(payment_method, "id", None)
            if not method_id:
                bot.send_message(
                    call.from_user.id,
                    "Не удалось получить payment_method_id из последней оплаты.",
                )
                return

            amount = payment_record.amount
            if amount is None:
                response_amount = getattr(response, "amount", None)
                amount = _safe_int(getattr(response_amount, "value", None))
            if amount is None:
                amount = 333

            product = payment_record.product or "subscribe-1"

            try:
                autopay = upsert_autopay_method(
                    session,
                    user.id,
                    method_id,
                    product,
                    amount,
                    payment_record.payment_id,
                )
                autopay.last_attempt_at = None
                session.commit()
            except Exception as exc:
                session.rollback()
                bot.send_message(call.from_user.id, f"Не удалось сохранить автоплатёж: {exc}")
                return

            try:
                bot.answer_callback_query(call.id, "Автоплатёж подключён")
            except:
                pass
            markup = types.InlineKeyboardMarkup()
            _append_autopay_button(markup, True)
            markup.add(types.InlineKeyboardButton("К разделу подписки", callback_data="subscribe"))
            bot.send_message(
                call.from_user.id,
                "Автопродление подписки подключено. Следующее списание произойдёт автоматически.",
                reply_markup=markup,
            )
        elif call.data == "subscribe-autopay-disable":
            if user is None:
                try:
                    bot.answer_callback_query(call.id, "Пользователь не найден")
                except:
                    pass
                return
            try:
                removed = delete_autopay_method(session, user.id)
                session.commit()
            except Exception as exc:
                session.rollback()
                bot.send_message(call.from_user.id, f"Не удалось отключить автоплатёж: {exc}")
                return

            if removed:
                try:
                    bot.answer_callback_query(call.id, "Автоплатёж отключён")
                except:
                    pass
                markup = types.InlineKeyboardMarkup()
                _append_autopay_button(markup, False)
                markup.add(types.InlineKeyboardButton("К разделу подписки", callback_data="subscribe"))
                bot.send_message(
                    call.from_user.id,
                    "Автопродление отключено. Оплачивайте подписку вручную, чтобы сохранить доступ.",
                    reply_markup=markup,
                )
            else:
                try:
                    bot.answer_callback_query(call.id, "Автоплатёж не был подключён")
                except:
                    pass
                bot.send_message(call.from_user.id, "У вас нет активного автоплатежа.")
        elif call.data == "_subscribe-send_forlove":
            bot.send_message(call.from_user.id, "Для получения реквизитов напишите: @RodionRa")
        #ПРОДУКТЫ
        elif call.data == "our_products":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Ведущий игры за 55 555 ₽", callback_data=f"buy-product_game_55555")
            button_pocket_game = types.InlineKeyboardButton("Карманная игра за 9 999 ₽", callback_data="buy-product_pocketgame_9999")
            button_bot = types.InlineKeyboardButton("Бот представителей за 9 999 ₽", callback_data=f"buy-product_personalbot_9999")
            button_service_card = types.InlineKeyboardButton("Сервисная карта за 4 444 ₽", callback_data="buy-product_servicecard_4444")
            #button = types.InlineKeyboardButton("Владелец сертификата за 15 555 ₽", callback_data=f"buy-product_game_55555")
            #button = types.InlineKeyboardButton("Управление городом за 15 555 ₽", callback_data=f"buy-product_game_55555")
            #button = types.InlineKeyboardButton("Организатор туров за 15 555 ₽", callback_data=f"buy-product_game_55555")
            #button = types.InlineKeyboardButton("Производитель/поставщик за 15 555 ₽", callback_data=f"buy-product_game_55555")
            
            button2 = types.InlineKeyboardButton("Организатор клуба знакомств за 99 999 ₽", callback_data=f"buy-product_clubtraining_99999")
            button3 = types.InlineKeyboardButton("Управляющий города за 333 333 ₽", callback_data=f"buy-product_citymanager_333333")
            
            markup.add(button, button_pocket_game, button_bot, button_service_card, button2, button3, row_width=1)
            
            if user.ref_level == 1: 
                button3 = types.InlineKeyboardButton("Пакет партнерской программы за 5000 ₽", callback_data=f"buy-product_package_5000")
                markup.add(button3)
            if user.ref_level == 2: 
                button4 = types.InlineKeyboardButton("Пакет партнерской программы за 15000 ₽", callback_data=f"buy-product_package_15000")
                markup.add(button4)
            if user.ref_level == 3:
                button5 = types.InlineKeyboardButton("Пакет партнерской программы за 25000 ₽", callback_data=f"buy-product_package_25000")
                markup.add(button5)
            if user.ref_level == 4:
                button6 = types.InlineKeyboardButton("Пакет партнерской программы за 45000 ₽", callback_data=f"buy-product_package_45000")
                markup.add(button6)
            if user.ref_level == 5: 
                button7 = types.InlineKeyboardButton("Пакет партнерской программы за 100000 ₽", callback_data=f"buy-product_package_100000")
                markup.add(button7)

            button8 = types.InlineKeyboardButton("Пакет партнерской программы с выгодой 50%", callback_data="buy-product_allpackage_99999")
            markup.add(button8)
            
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/MTdfRKXb/photo-2025-08-20-16-34-22.jpg",caption= """
Хотите зарабатывать, делясь ценностями 'За любовь'?
Наша бизнес-модель открывает множество возможностей: от проведения игр до управления городом или создания контента. 

Выберите роль, которая вам ближе, и начните свой путь к финансовой свободе и вдохновению. Мы поддержим вас на каждом шагу: предоставим обучение, маркетинговые материалы и доступ к нашей экосистеме!    
""",reply_markup=markup)
        elif call.data.startswith("buy-product"):
            name = call.data.split("_")[1]
            price = call.data.split("_")[2]
            
            procent_balance = 25
            inner_balance = 25
            if name == "personalbot":
                procent_balance = 30
                inner_balance = 0
            elif name == "servicecard":
                procent_balance = 30
                inner_balance = 0
            elif name == "pocketgame":
                procent_balance = 20
                inner_balance = 0

            pay_metadata = PayMetadata(
                user_id = user.id,
                price = price,
                product = name,
                procent_balance = procent_balance,
                inner_balance = inner_balance
            )
            
            session.add(pay_metadata)
            session.commit()
            
            idempotence_key = str(uuid.uuid4())
            
            payment = Payment.create(
                {
                    "id": idempotence_key,
                    "amount": {
                        "value": price,
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": "https://t.me/forlove2025_bot"
                    },
                    "capture": True,
                    "description": pay_metadata.id,
                    "metadata": {
                        'orderNumber': pay_metadata.id
                    },
                    "receipt": {
                        "customer": {
                            "full_name": "Николаев Артем Алексеевич",
                            "email": "cfznyjdf13@mail.ru",
                            "phone": "79166758299",
                            "inn": "170108382176"
                        },
                        "items": [
                            {
                                "description": "Пакет",
                                "quantity": "1.00",
                                "amount": {
                                    "value": price,
                                    "currency": "RUB"
                                },
                                "vat_code": "2",
                                "payment_mode": "full_payment",
                                "payment_subject": "commodity",
                                "country_of_origin_code": "RU",
                                "product_code": "44 4D 01 00 21 FA 41 00 23 05 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 12 00 AB 00",
                                "customs_declaration_number": "10714040/140917/0090376",
                                "excise": "20.00",
                                "supplier": {
                                    "name": "string",
                                    "phone": "string",
                                    "inn": "string"
                                }
                            },
                        ]
                    },
                }, 
                idempotency_key=idempotence_key
            )
            
            confirmation_url = payment.confirmation.confirmation_url
            
            markup = types.InlineKeyboardMarkup()    
            button = types.InlineKeyboardButton(f"Оплатить ({price} ₽)", url=confirmation_url)
            #button2 = types.InlineKeyboardButton(f"Проверить оплату", callback_data=f"check-buy-product_{pay_metadata.id}")
            markup.add(button, row_width=1)
            
            
            
            text = ""
            if name == "game":
                image_url = "https://iimg.su/s/17/WjbY8Fs5oXFRxx3LDZV9yUSzQjtvA2BCBQWwMad1.png"
                text = """
КОМПЛЕКТ ВЕДУЩЕГО ИГР

Мы присылаем вам комплект настольной игры, с ним вы сможете проводить игры в своем городе и зарабатывать на этом. Инструкции и базовое обучение также прилагается.
Вы будете получать доход от проведения игр и бонусы по партнерской программе.
Стоимость: 55.555 руб.
Прогназируемая окупаемость: 1-2 месяца.

https://rutube.ru/video/04c84f87f4dd9de603169e98aa5c9f41/?r=a
                """
            elif name == "pocketgame":
                image_url = "assets/game.jpg"
                text = """
💌 Карманная игра “За Любовь”

Небольшая коробочка, а возможностей — как у вселенной. ✨
Эта мини-версия большой игры создана, чтобы мягко и красиво знакомить людей с проектом «За Любовь».

Через лёгкий формат, пару неожиданных вопросов и один  тёплый разговор — человек вдруг понимает,
что здесь про настоящее, про ценности, про людей… и хочется остаться дольше.

🌸 Для ведущих — это не просто игра, а волшебный инструмент:
помогает знакомить с проектом, выстраивать контакт и мягко переводить людей к следующим шагам —
подписка, участие в большой игре, партнёрство и другие чудеса.

💬 Для участников — это способ поговорить по-настоящему.
Без неловкости, без “как дела?”, а с душой: о чувствах, о близости, о себе.
Можно играть вдвоём, с друзьями или даже на мероприятии — и каждый раз будет что-то новое, живое, настоящее.

💰 Стоимость: 9 999 ₽

https://rutube.ru/video/c56aa176e1cdf95d36dc599c4fec8e29/?r=a
                """
            elif name == "clubtraining":
                image_url = "https://iimg.su/s/17/tAG14iNFiiiGpLTVv4o9Ip07onLPoN3IQ6wMrinK.png"
                text = """
ОБУЧАЮЩИЙ КУРС "ОРГАНИЗАТОР КЛУБА ОСОЗНАННЫХ ЗНАКОМСТВ"

Мы присылаем вам комплект настольной игры, с ним вы сможете проводить игры в своем городе и зарабатывать на этом. Инструкции и базовое обучение прилагается.
Также вы сможете организовывать мероприятия, туры, фестивали от нашей компании.
Вы будете получать доход от проведения игр и других мероприятий, и бонусы по партнерской программе.
Стоимость: 79.999 руб.
Прогназируемая окупаемость: 1-2 месяца.                

https://rutube.ru/video/3f2b65b609effaec08787b7362423a0e/?r=a
"""
            elif name == "package":
                text = """
Возможность расширить заработок с реферальной программы
"""
                image_url = None
            elif name == "allpackage":
                text = """
Покупка всех пакетов с выгодой 50% для расширения заработка с реферальной программы
"""
                image_url = None
            elif name == "personalbot":
                text = """
💫 Новый уровень для ведущих «За Любовь»

Теперь у каждого ведущего может быть свой личный бот —
маленький, но очень умный помощник, который работает за вас,
пока вы занимаетесь самым важным — живыми встречами и играми.

В нём всё, чтобы ваши игры стали ещё живее, а организация — легче:
💌 автоматическая регистрация участников
🎁 персональные скидки и акции именно от вас
🛍 ваш личный интернет-магазин — возможность продавать свои товары и услуги прямо через бота, а также продукты партнёров, с кем вы сотрудничаете
📢 новости и рассылки по вашей аудитории
💛 место, где собирается и растёт ваше сообщество — с вашим стилем, вашим голосом, вашей энергией

Теперь каждый ведущий — не просто часть проекта,
а создатель своей мини-вселенной «За Любовь» —
со своими участниками, предложениями и вдохновением.

✨ Приобрести своего бота можно по кнопке ниже.
А если хотите узнать подробнее о нём — напишите @irrrun, Ирина всё расскажет.

Пора сделать любовь ещё ближе. ❤️
"""
                image_url = "assets/city_bot.jpg"
            elif name == "servicecard":
                text = """💛 Сервисная карта «За Любовь»

Ваш мягкий вход в нашу экосистему заботы, выгод и новых возможностей.
Средняя выгода по карте — от 100 000 ₽ 

Сервисная карта — это не просто продукт, а пропуск в пространство, где экономия соединяется с вниманием, а возможности — с человеческим теплом.

🌿 Что даёт карта?

✨ Экономия
Доступ к каталогу скидок, бесплатных услуг и привилегий от наших партнёров. Простая ежедневная забота о бюджете.

✨ Доход от рекомендаций
Делитесь картой — и получайте бонусы с людей, которые присоединяются по вашей ссылке.

✨ Инструмент для бизнеса
Укрепляет лояльность клиентов: можно дарить, использовать как мотивацию или продавать.

✨ Активный доход
Бонус за каждую личную рекомендацию — лёгкий способ начать зарабатывать внутри экосистемы.

📌 Полный список партнёров, привилегий и сервисов — в видео и презентации ниже.

Стоимость — 4 444 ₽,
и эта сумма открывает доступ ко всей платформе.

https://rutube.ru/video/617a57bc21193de01b3a3047f40310e7/?r=a/
"""
                image_url = "assets/service_card.jpg"
            elif name == "citymanager":
                image_url = "https://i.postimg.cc/4yYZ7DJL/photo-2025-08-21-16-03-53.jpg"
                text = """
Роль управляющего города позволит вам:

- БЫТЬ всегда в Первой Строке списка клубов знакомств по вашему городу

- ИМЕТЬ бесконечную глубину по партнерской программе

- ПРОВОДИТЬ ИГРУ ЗАЛЮБОВЬ В ЛЮБОЙ ТОЧКЕ МИРА ОФЛАЙН

- ОБУЧАТЬ ИГРЕ ЗАЛЮБОВЬ

- ОРГАНИЗОВЫВАТЬ 2-3 дневные туры в СПБ /ПРИСОЕДИНЯТЬСЯ к существующим мероприятиям 

- ПОДКЛЮЧАТЬ сообщества к проекту ЗАЛЮБОВЬ: танцевальные клубы, йога центры, ЗОЖ, любителей животных, яхт клубы, авто-спорт клубы, тренинги по личностному росту, нетворкинг-сообщества, брачные агенства по организации свадеб и все направления какие есть, направленные на развитие.

- РАЗМЕЩАТЬ свои услуги на маркетплейсе платформы

- ПОЛУЧАТЬ скидки и бонусы от всех уча,тников международного проекта ЗАЛЮБОВЬ

- ДРУЖИТЬ С АНГЕЛАМИ НА ЗЕМЛЕ ПО ВСЕМУ МИРУ

- ПОМОГАТЬ ЛЮДЯМ СОЕДИНЯТЬ СЕРДЦА 

- ДАРИТЬ СВОЮ ЛЮБОВЬ РАДИ ЖИЗНИ НА ЗЕМЛЕ ВСЕГО ЧЕЛОВЕЧЕСТВА"""            
            if image_url:
                if image_url.startswith("http"):
                    bot.send_photo(call.from_user.id, image_url, text, reply_markup=markup)
                else:
                    with open(image_url, "rb") as photo:
                        bot.send_photo(call.from_user.id, photo, text, reply_markup=markup)
            else:
                bot.send_message(call.from_user.id, text, reply_markup=markup)
        elif call.data == "_buy-product_forlove":
            bot.send_message(call.from_user.id, "Для получения реквизитов напишите: @RodionRa")
          
        #МЕРОПРИЯТИЯ
        elif call.data == "our_events":
            markup = types.InlineKeyboardMarkup()    
            button = types.InlineKeyboardButton("Форматы мероприятий", callback_data="event_formats")
            markup.add(button, row_width=1)
            
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/VkcvsnH3/photo-2025-08-20-16-20-21.jpg", """
Проект 'За любовь' — это не только игры, но и яркие оффлайн-мероприятия: фестивали знакомств, туры, конкурсы красоты и вдохновляющие встречи. 

Каждое событие создано, чтобы объединять людей, помогать находить друзей, партнеров или единомышленников. 
Узнайте больше о наших форматах, посмотрите расписание или станьте гидом, чтобы организовывать события в своем городе!
                             """, reply_markup=markup)
        elif call.data == "organize_events":
            bot.send_message(call.message.chat.id, "Если вы хотите организовать свое мероприятия при нашей поддержке, напишите: @irrrun")
        elif call.data == "event_formats":
            markup = types.InlineKeyboardMarkup()    
            button = types.InlineKeyboardButton("Туры знакомств", callback_data="event_tours")
            button2 = types.InlineKeyboardButton("Презентации онлайн", callback_data="event_forlove")
            button3 = types.InlineKeyboardButton("Презентации компаний", callback_data="event_forlove")
            button4 = types.InlineKeyboardButton("Мероприятия партнеров", callback_data="event_forlove")
            
            markup.add(button, button2, button3, button4, row_width=2)
            
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/tCMtRdnq/photo-2025-08-19-14-38-26.jpg", caption="""
Мы проводим разные форматы мероприятий, чтобы каждый нашел что-то для себя. 
Выберите, что вас вдохновляет: фестивали, туры, конкурсы или мастер-классы.
Для более подробной информации зайдите в наш основной канал: t.me/za_lyubov_igra
                             """, reply_markup=markup)
        #elif call.data == "event_tours":
            
        elif call.data == "event_forlove":
            bot.send_message(call.from_user.id, """Для более подробной информации зайдите в наш основной канал: t.me/za_lyubov_igra""")
        elif call.data == "_event_festival":
            bot.send_message(call.from_user.id, """Инфа про Фестиваль""")
        elif call.data == "_event_conferences":
            bot.send_message(call.from_user.id, """Инфа про Конференции""")
        elif call.data == "event_table":
            today = datetime.now().strftime("%d.%m")
            
            stmt = select(Schedule).where(Schedule.start >= today) # поправить баг с отображением расписания
            results = session.execute(stmt)
            schedules = results.scalars().all()
            markup = types.InlineKeyboardMarkup()    
            for schedule in schedules: 
                button = types.InlineKeyboardButton(f"{schedule.name}, {schedule.city}, {schedule.start}", callback_data=f"event_table_inner-{schedule.id}")
                markup.add(button, row_width=1)
            addiction_text = ""
            if len(schedules) == 0: addiction_text = "Расписание появится скоро"
            bot.send_message(call.from_user.id, f"""
Ознакомьтесь с расписанием наших мероприятий и выберите то, что вам интересно! От фестивалей до локальных встреч — у нас всегда есть что-то особенное.

{addiction_text}
                             """, reply_markup=markup)
        elif call.data.startswith("event_table_inner"):
            schedule_id = int(call.data.split("-")[1])
            schedule = session.execute(select(Schedule).where(Schedule.id == schedule_id)).scalar()
            
            pay_link = "https://example.com"
            
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Купить сертификат", callback_data="inner_event_table_text")
            markup.add(button)
            
            bot.send_message(call.from_user.id, f"""
Информация:
{schedule.name}, {schedule.city}, {schedule.start}
""", reply_markup=markup)
        elif call.data == "inner_event_table_text":
            bot.send_message(call.from_user.id, f"Для получения реквизитов и дальнейших инструкций обратитесь к @RodionRa")
        
        elif call.data == "become_guide":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Оставить заявку", callback_data="become_guide_stay")
            markup.add(button)
            bot.send_message(call.from_user.id, f"""
Мечтаете организовывать туры и мероприятия 'За любовь' в вашем городе? 

Станьте гидом и вдохновляйте людей на новые знакомства и развитие! Мы предоставим вам обучение, материалы и поддержку, чтобы вы могли создавать незабываемые события. Узнайте, как начать, и подайте заявку!
Для более подробной информации напишите: @RodionRa
""", reply_markup=markup)
        
        elif call.data == "become_guide_stay":
            bot.send_message(call.from_user.id, f"Ваша заявка отправлена")
            bot.send_message(61886854, f"Заявка от @{user.username} на 'Гида'")
        
        # РЕФЕРАЛЬНАЯ СИСТЕМА
        elif call.data == "ref_program":
            markup = types.InlineKeyboardMarkup()
            button5 = types.InlineKeyboardButton("Поделиться ссылкой", url=f"https://t.me/share/url?url=https://t.me/forlove2025_bot?start={call.from_user.id}")
            button = types.InlineKeyboardButton("Моя структура", callback_data="ref_structure")
            button2 = types.InlineKeyboardButton("Перевод средств", callback_data="transfer_balance")
            button3 = types.InlineKeyboardButton("Заявка на вывод", callback_data="return_balance")
            button4 = types.InlineKeyboardButton("Сменить спонсора", callback_data="change_sponsor")
            button6 = types.InlineKeyboardButton("Подробнее о партнерке", callback_data="about_ref_program")
            markup.add(button5, button, button2, button3, button4, button6, row_width=1)
            
            # Days left
            days_left = get_subscription_days_left(session, user.id)
            days_left_text = format_subscription_remaining(days_left)

            bot.send_photo(call.from_user.id, "https://i.postimg.cc/7ZmGGZcH/photo-2025-08-20-16-24-14.jpg", f"""
Зарабатывайте, приглашая друзей в проект 'За любовь'! Наша реферальная программа позволяет вам получать доход от подписок, игр и со всех других продуктов, которыми делятся ваши приглашенные. Чем больше ваша команда, тем выше ваш заработок — с ветки партнерской сети до бесконечености. Получите свою уникальную ссылку, следите за балансом и стройте свою структуру уже сегодня!

Реферальная ссылка (Нажмите один раз на ссылку ниже и она скопируется): 

➡️<code>https://t.me/forlove2025_bot?start={call.from_user.id}</code>⬅️

Мой спонсор:
@{get_user_ref(session, user).username}

Бонусный баланс:
{user.balance} ₽

Накопительный баланс:
{user.inner_balance} ₽

Подписка действует ещё:
{days_left_text}
                             """, reply_markup=markup, parse_mode="html")
        elif call.data == "ref_structure":
            ref_users = session.execute(select(User).where(User.ref == user.tg_id)).scalars().all() # реферальная структура
            nicks = """"""
            for ref in ref_users:
                nicks += f"@{ref.username}\n"
            
            users = session.execute(select(User).where(User.ref == user.tg_id)).scalars().all()
            line_users = []
            text_line = ""
            for i in range(0, 20):
                line_users.append(len(users))
                if len(users) != 0: text_line += f"Пользователей в {i + 1} линии: {len(users)}\n"
                users = get_list_refs(session, users)
            print(line_users)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Открыть дерево", f"https://hamsterdev-code-forlove-a23b.twc1.net?{user.tg_id}"))
            bot.send_message(call.from_user.id, f"""
Посмотрите, как растет ваша команда! Здесь вы можете увидеть участников вашей первой линии, чтобы отслеживать свой прогресс. Создавайте сообщество единомышленников и зарабатывайте вместе!

{text_line}

Ваша 1-я линия:
{nicks}   
                             """, reply_markup=markup)
        elif call.data == "return_balance":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Открыть тех поддержку", callback_data="support"))
            bot.send_message(call.from_user.id, """
Инструкция на вывод денежных средств:

1. Ваш статус должен соответствовать ИП (ООО).
2. Заключить агенский договор через тех поддержку
3. Подать заявку на вывод (30000 бонусов) 
                            """, reply_markup=markup)
            bot.send_message(ADMIN_CHAT_ID, f"Заявка на вывод средств от @{user.username} (его баланс - {user.balance} ₽)", message_thread_id=6)
        elif call.data == "transfer_balance":
            bot.send_message(call.from_user.id, "Вы можете перевести средства с бонусного баланса. Напишите ник кому вы хотите перевести (в формате @ник)")
            bot.register_next_step_handler(call.message, transfer_balance_1, bot)
        elif call.data == "about_ref_program":
            pdf_file = open("assets/Бонусная_партнерская_программа_За_любовь.pdf" , "rb")
            bot.send_document(call.from_user.id, pdf_file)
            xlsx_file = open("assets/Калькулятор ПП За любовь.xlsx", "rb")
            bot.send_document(call.from_user.id, xlsx_file)
            bot.send_message(call.message.chat.id, "https://rutube.ru/video/4a15e34316ff713ed345842df1134729/?r=a/")
        elif call.data == "change_sponsor":
            bot.send_message(call.from_user.id, f"Напишите ник под кого вы хотите перейти (в формате @ник)")
            bot.register_next_step_handler(call.message, change_sponsor_1, bot)
        # ПОДДЕРЖКА
        elif call.data == "support":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Отправить вопрос в поддержку", callback_data="support_message")
            markup.add(button)
            bot.send_photo(call.from_user.id, "https://i.postimg.cc/fWvQcSzh/photo-2025-08-20-16-36-49.jpg", "У вас есть вопросы или нужна помощь? Мы всегда рядом!\n\nНапишите нам, расскажите о вашей ситуации или задайте вопрос, и наша команда поддержки ответит в кратчайшие сроки. Если хотите, прикрепите фото, чтобы мы лучше поняли ваш запрос. Давайте сделаем ваш опыт с 'За любовь' незабываемым!", reply_markup=markup)
        elif call.data == "support_message":
            bot.send_message(call.from_user.id, "Отправьте вопрос в поддержку. Обращение рассматривается в течение 24 часов в рабочие дни")
            bot.register_next_step_handler(call.message, support_message, bot)
        elif call.data == "support_tech":
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Отправить сообщение в поддержку", callback_data="support_message_tech")
            markup.add(button)
            bot.send_message(call.from_user.id, "Опишите свою проблему по кнопке ниже", reply_markup=markup)
        elif call.data == "support_message_tech":
            bot.send_message(call.from_user.id, "Отправьте сообщение в поддержку. Обращение рассматривается в течение 24 часов в рабочие дни")
            bot.register_next_step_handler(call.message, support_message_tech, bot)
    if call.id: bot.answer_callback_query(call.id)  # Теперь у вас открылись все возможности нашей платформы      
    
def _education_expert_submit(message: types.Message, bot: TeleBot):
    if message.text == "На главную":
        handle_start_message(bot, message.chat.id)
        return
    if message.content_type != "text":
        bot.send_message(message.chat.id, "Пожалуйста, отправьте заявку текстом.")
        bot.register_next_step_handler(message, _education_expert_submit, bot)
        return

    application_text = message.text.strip()
    if not application_text:
        bot.send_message(message.chat.id, "Сообщение пустое. Напишите заявку ещё раз.")
        bot.register_next_step_handler(message, _education_expert_submit, bot)
        return

    with Session(engine) as session:
        user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar()

    author = _format_user(user, message.from_user.id)
    admin_message = (
        "🚀 Новая заявка «Стать экспертом»\n"
        f"От: {author}\n\n"
        f"{application_text}"
    )

    admin_kwargs = {
        "chat_id": ADMIN_CHAT_ID,
        "text": admin_message,
    }
    if ADMIN_EDUCATION_THREAD_ID:
        admin_kwargs["message_thread_id"] = ADMIN_EDUCATION_THREAD_ID

    try:
        bot.send_message(**admin_kwargs)
    except Exception as exc:
        try:
            print(f"[education] failed to forward expert application: {exc}")
        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        "Спасибо! Мы передали заявку куратору. Он свяжется с вами в ближайшее время.",
    )


def _strategy_partners_submit(message: types.Message, bot: TeleBot):
    if message.text == "На главную":
        handle_start_message(bot, message.chat.id)
        return
    if message.content_type != "text":
        bot.send_message(message.chat.id, "Пожалуйста, отправьте заявку текстом.")
        bot.register_next_step_handler(message, _strategy_partners_submit, bot)
        return

    application_text = message.text.strip()
    if not application_text:
        bot.send_message(message.chat.id, "Сообщение пустое. Напишите заявку ещё раз.")
        bot.register_next_step_handler(message, _strategy_partners_submit, bot)
        return

    with Session(engine) as session:
        user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar()

    author = _format_user(user, message.from_user.id)
    admin_message = (
        "🤝 Новая заявка «Стать стратегическим партнёром»\n"
        f"От: {author}\n\n"
        f"{application_text}"
    )

    admin_kwargs = {
        "chat_id": ADMIN_CHAT_ID,
        "text": admin_message,
    }
    if ADMIN_EDUCATION_THREAD_ID:
        admin_kwargs["message_thread_id"] = ADMIN_EDUCATION_THREAD_ID

    try:
        bot.send_message(**admin_kwargs)
    except Exception as exc:
        try:
            print(f"[strategy_partners] failed to forward partner application: {exc}")
        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        "Спасибо! Мы передали заявку куратору. Он свяжется с вами в ближайшее время.",
    )

def support_message(message: types.Message, bot: TeleBot):
    bot.send_message(message.chat.id, "Вопрос отправлен в поддержку")
    bot.send_message(ADMIN_CHAT_ID, f"""
Пользователь @{message.from_user.username} отправил сообщение в поддержку:

{message.text}
                     """, message_thread_id=7)
def support_message_tech(message: types.Message, bot: TeleBot):
    bot.send_message(message.chat.id, "Сообщение отправлено в поддержку")
    bot.send_message(ADMIN_CHAT_ID, f"""
Пользователь @{message.from_user.username} отправил сообщение в поддержку:

{message.text}
                     """, message_thread_id=70)

def change_sponsor_1(message: types.Message, bot: TeleBot):
    if message.text == "На главную":
        handle_start_message(bot, message.chat.id)
        return
    new_sponsor = message.text[1:]
    bot.send_message(message.chat.id, "Вы точно уверены в смене спонсора? Введите «Да»")
    bot.register_next_step_handler(message, change_sponsor_2, bot, new_sponsor)
def change_sponsor_2(message: types.Message, bot: TeleBot, new_sponsor: str):
    if message.text == "На главную": 
        handle_start_message(bot, message.chat.id)
        return
    
    if "да" in message.text.lower():
        with Session(engine) as session:
            ref_user = session.execute(select(User).where(User.username == new_sponsor)).scalar()
            if ref_user == None: 
                bot.send_message(message.chat.id, "Спонсор не найден.")
                #bot.send_message(message.chat.id, f"Напишите ник под кого вы хотите перейти (в формате @ник)")
                #bot.register_next_step_handler(message, change_sponsor_1, bot)
                return
            bot.send_message(message.chat.id, "Спонсор успешно изменен")
            user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar()
            user.ref = ref_user.tg_id
            session.commit()
                
    else:
        bot.send_message(message.chat.id, "Изменение спонсора отменено")

def transfer_balance_1(message: types.Message, bot: TeleBot):
    if message.text == "На главную": 
        handle_start_message(bot, message.chat.id)
        return
    if 'отмена' in message.text.lower():
        bot.send_message(message.chat.id, "Отправка баланса отменена")
        return
    with Session(engine) as session:
        balance_get_user = session.execute(select(User).where(User.username == message.text[1:])).scalar()
        if balance_get_user == None:
            bot.send_message(message.chat.id, "Пользователь не найден")
        else:
            bot.send_message(message.chat.id, f"Введите сумму которую вы хотите перевести к @{balance_get_user.username}")
            bot.register_next_step_handler(message, transfer_balance_2, bot, message.text[1:])
def transfer_balance_2(message: types.Message, bot: TeleBot, username: str):
    with Session(engine) as session:
        balance_get_user = session.execute(select(User).where(User.username == username)).scalar()
        user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar()
        try: 
            number = int(message.text)
            if user.balance < number: 
                bot.send_message(message.chat.id, "На балансе меньше введеной суммы")
                return
        except: bot.send_message(message.chat.id, "На балансе меньше введеной суммы")
        balance_get_user.balance += number
        user.balance -= number
        session.commit()
        transfer = BalanceTransfer(
            from_user_id = user.id,
            to_user_id = balance_get_user.id,
            money = number
        )
        session.add(transfer)
        session.commit()
        bot.send_message(message.chat.id, f"Успешно отправлено {number} ₽ на баланс @{balance_get_user.username}")
        bot.send_message(balance_get_user.tg_id, f"Вы получили {number} ₽ на баланс от @{user.username}")


# ₽
