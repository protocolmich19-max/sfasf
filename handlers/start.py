from sqlalchemy.orm import Session
from telebot import types, TeleBot
from db.handlers import create_user, get_user
from db.connect import engine
from yookassa import Configuration, Payment
import uuid
import config
from db.models import PayMetadata
from handlers.subscription_checker import has_active_subscription

# Инициализация YooKassa из конфигурации
Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_API)

def handle_start_message(bot: TeleBot, chat_id: int, has_new_message = False):
    if has_new_message:
        bot.send_message(chat_id, """
<a href="http://user-agreement.integrocore.com/forlove2">Пользовательское соглашение</a>
<a href="http://privacy-policy.integrocore.com/forlove1">Политика конфиденциальности</a>
                         """, parse_mode='html')

    # Always show a small reply keyboard with "На главную"
    reply_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reply_kb.add(types.KeyboardButton('На главную'))

    # Determine subscription status
    with Session(engine) as session:
        user = get_user(session, chat_id)
        is_active = False
        if user:
            try:
                is_active = has_active_subscription(session, user.id)
            except Exception:
                is_active = False

    if not is_active:
        # Subscription-only gate
        markup = types.InlineKeyboardMarkup()
        btn_m1 = types.InlineKeyboardButton("Оформить на месяц (333 ₽)", callback_data="buy-subscribe_1_333")
        btn_y1 = types.InlineKeyboardButton("Оформить на год (3333 ₽)", callback_data="buy-subscribe_12_3333")
        markup.add(btn_m1, btn_y1, row_width=1)
        bot.send_message(chat_id, "\n\nВаша подписка неактивна. Доступ к разделам будет открыт после оплаты.", reply_markup=reply_kb)
        bot.send_photo(chat_id, "https://s3.iimg.su/s/15/g3fqZ2AxMZ1uyqVv8WglGq923WJdcXeoMNCrSzlJ.png", caption="Оформите подписку, чтобы открыть доступ ко всем разделам платформы.", reply_markup=markup)
        return

    # Full menu when subscription is active
    bot.send_message(chat_id, "Спасибо, что присоединились к нам! 🎉", reply_markup=reply_kb)

    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("О проекте",callback_data="about_project")
    button2 = types.InlineKeyboardButton("Наши города",callback_data="our_cities")
    button3 = types.InlineKeyboardButton("Подписка",callback_data="subscribe")
    button4 = types.InlineKeyboardButton("Медиа / Материалы",callback_data="media_channels")
    button5 = types.InlineKeyboardButton("Наши мероприятия", callback_data="our_events")   
    button6 = types.InlineKeyboardButton("Наши продукты", callback_data="our_products")   
    button10 = types.InlineKeyboardButton("Образовательный контент", callback_data="education_content")
    button11 = types.InlineKeyboardButton("Стратегические партнеры", callback_data="strategy_partners_content")

    markup.add(button1, button2, button3, button6, button10, button11, button5, button4, row_width=2)
    button8 = types.InlineKeyboardButton("Техническая поддержка", callback_data="support_tech")   
    button9 = types.InlineKeyboardButton("Предложения руководству", callback_data="support")   
    button7 = types.InlineKeyboardButton("Партнёрская программа и баланс", callback_data="ref_program")   

    markup.add(button8, button9, row_width=2)
    markup.add(button7, row_width=1)
    bot.send_photo(chat_id, "https://i.postimg.cc/W1v6Dthv/photo-2025-08-18-18-05-19.jpg", caption="Проект 'За любовь' — это движение, которое объединяет людей, стремящихся к осознанным отношениям, личностному росту и вдохновляющему сообществу.\n\nЧерез наши игры, курсы, клубы знакомств и партнерскую программу вы найдете новые возможности для счастья и успеха. Выберите раздел, чтобы узнать больше:", reply_markup=markup)
    
    


def handler_start(bot: TeleBot, message: types.Message):
    go_code = None

    with Session(engine) as session:
        user = get_user(session, message.from_user.id)
        
        if " " in message.text:
            go_code = message.text.split()[1]
            if go_code == "pay_199" and user != None:
                with Session(engine) as session:
                
                    idempotence_key = str(uuid.uuid4())
                    
                    pay_metadata = PayMetadata(
                        user_id = user.id,
                        price = 199,
                        product = "poster",
                        procent_balance = 10,
                        inner_balance = 0
                    )
                    session.add(pay_metadata)
                    session.commit()
                
                    payment = Payment.create(
                        {
                            "id": idempotence_key,
                            "amount": {
                                "value": 199,
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
                                            "value": 199,
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
                    markup.add(types.InlineKeyboardButton("Оплатить создание афиши", url=confirmation_url))
                    bot.send_message(message.chat.id, '''
Вы оплачиваете 199 руб за создание афиши в едином фирменном стиле игры "За любовь". 
Готовую афишу вышлем Вам в чате ведущих в течение 1 суток после оплаты.

Спасибо , что поддерживаете нас и наш фирменный стиль ❤️''', reply_markup=markup)
                    
                    return
            if go_code == "pay_199_2" and user != None:
                with Session(engine) as session:
                
                    idempotence_key = str(uuid.uuid4())
                    
                    pay_metadata = PayMetadata(
                        user_id = user.id,
                        price = 199,
                        product = "poster",
                        procent_balance = 10,
                        inner_balance = 0
                    )
                    session.add(pay_metadata)
                    session.commit()
                
                    payment = Payment.create(
                        {
                            "id": idempotence_key,
                            "amount": {
                                "value": 199,
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
                                            "value": 199,
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
                    markup.add(types.InlineKeyboardButton("Оплатить создание визитки", url=confirmation_url))
                    bot.send_message(message.chat.id, '''
Вы оплачиваете 199 руб за создание вашей визитки в едином фирменном стиле игры "За любовь". 
Готовую визитку вышлем Вам в чате ведущих в течение 1 суток после оплаты. 

Спасибо, что поддерживаете нас и наш фирменный стиль ❤️''', reply_markup=markup)
                    
                    return
            if go_code == "our_products" and user != None:
                markup = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("Ведущий игры за 55555 ₽", callback_data=f"buy-product_game_55555")
                button_pocket_game = types.InlineKeyboardButton("Карманная игра за 9 999 ₽", callback_data="buy-product_pocketgame_9999")
                button_service_card = types.InlineKeyboardButton("Сервисная карта за 4 444 ₽", callback_data="buy-product_servicecard_4444")
                
                #button = types.InlineKeyboardButton("Владелец сертификата за 15 555 ₽", callback_data=f"buy-product_game_55555")
                #button = types.InlineKeyboardButton("Управление городом за 15 555 ₽", callback_data=f"buy-product_game_55555")
                #button = types.InlineKeyboardButton("Организатор туров за 15 555 ₽", callback_data=f"buy-product_game_55555")
                #button = types.InlineKeyboardButton("Производитель/поставщик за 15 555 ₽", callback_data=f"buy-product_game_55555")
                
                button2 = types.InlineKeyboardButton("Организатор Клуба знакомств за 79999 ₽", callback_data=f"buy-product_clubtraining_79999")
                button3 = types.InlineKeyboardButton("Управляющий Города за 333333 ₽", callback_data=f"buy-product_citymanager_333333")
                
                markup.add(button, button_pocket_game, button_service_card, button2, button3, row_width=1)
                
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
                
                bot.send_photo(user.tg_id, "https://i.postimg.cc/MTdfRKXb/photo-2025-08-20-16-34-22.jpg",caption= """
    Хотите зарабатывать, делясь ценностями 'За любовь'?
    Наша бизнес-модель открывает множество возможностей: от проведения игр до управления городом или создания контента. 

    Выберите роль, которая вам ближе, и начните свой путь к финансовой свободе и вдохновению. Мы поддержим вас на каждом шагу: предоставим обучение, маркетинговые материалы и доступ к нашей экосистеме!    
    """,reply_markup=markup)
                return
        if go_code == "subscribe" and user != None:
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("На месяц за 333 ₽", callback_data=f"buy-subscribe_1_333")
            button2 = types.InlineKeyboardButton("На год за 3333 ₽", callback_data=f"buy-subscribe_12_3333")
            markup.add(button,button2, row_width=1)
            video = open("assets/subscribe.mp4", 'rb')
            bot.send_video(message.from_user.id, video, duration=10, caption="""
Подписка 'За любовь' — это ваш ключ к полной экосистеме проекта! За 333 руб./мес. (первый месяц бесплатно) вы получаете доступ к эксклюзивным образовательным курсам по психологии отношений, эмоциональному интеллекту и личностному росту, а также к маркетплейсу, партнерской программе и закрытым мероприятиям. 

Это ваш шанс учиться, общаться и зарабатывать в одном месте. Также вы сможете начать зарабатывать по партнерской программе.

Оформите подписку и начните свое путешествие к гармонии

https://rutube.ru/video/3641a629d7c72c037332444530a1636b/?r=a/""", reply_markup=markup)
            return
        if go_code == "service_card" and user != None:
            price=4444
            name = "servicecard"
            procent_balance = 30
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
            if image_url:
                if image_url.startswith("http"):
                    bot.send_photo(message.chat.id, image_url, text, reply_markup=markup)
                else:
                    with open(image_url, "rb") as photo:
                        bot.send_photo(message.chat.id, photo, text, reply_markup=markup)
            else:
                bot.send_message(message.chat.id, text, reply_markup=markup)
            return
        if user and user.has_ended:            
            handle_start_message(bot, message.chat.id)
        else:
            if not user:
                ref = 1
                if " " in message.text:
                    referrer_candidate = message.text.split()[1]
                    
                    # Пробуем преобразовать строку в число
                    try:
                        referrer_candidate = int(referrer_candidate)

                        # Проверяем на несоответствие TG ID пользователя TG ID реферера
                        if message.from_user.id != referrer_candidate: 
                            ref = referrer_candidate
                    except ValueError:
                        pass
                user = create_user(
                    session, 
                    message.chat.id, 
                    message.from_user.full_name, 
                    message.from_user.username,
                    ref
                )
                
                if ref != 1:
                    bot.send_message(ref, f"Пользователь @{user.username} зарегистрировался по вашей ссылке")
            
            if user.city == "":
                bot.send_message(message.chat.id, """
Добро пожаловать в мир 'За любовь'! 🌟 \n\nМы создали уникальную экосистему, чтобы помочь вам строить гармоничные отношения, находить единомышленников и раскрывать свой потенциал. Чтобы мы могли предложить вам самые актуальные мероприятия, игры и возможности в вашем регионе, пожалуйста, укажите ваш город и поделитесь номером телефона, привязанным к Telegram. Это займет всего минуту!""")
                msg = bot.send_message(message.chat.id, "Из какого вы города?")
                bot.register_next_step_handler(msg, handler_city, bot)
            elif user.phone == "":
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                reg_button = types.KeyboardButton(text="Отправить номер телефона", 
                request_contact=True)
                keyboard.add(reg_button)
                bot.send_message(message.chat.id, "Подвердите свой номер телефона, нажав кнопку, либо введите другой в формате +7XXXXXXXXXX или 8XXXXXXXXXX", reply_markup=keyboard)
                bot.register_next_step_handler(message, handle_phone, bot)
                
            
def handler_city(message: types.Message, bot: TeleBot):
    if message.text.startswith("/") or len(message.text) < 3:
        bot.send_message(message.chat.id, "Введите корректный город")
        bot.register_next_step_handler(message, handler_city, bot)
    else:
        with Session(engine) as session:
            user = get_user(session, message.chat.id)
            user.city = message.text
            session.commit()
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            reg_button = types.KeyboardButton(text="Отправить номер телефона", 
            request_contact=True)
            keyboard.add(reg_button)
            bot.send_message(message.chat.id, "Подвердите свой номер телефона, нажав кнопку, либо введите другой в формате +7XXXXXXXXXX или 8XXXXXXXXXX", reply_markup=keyboard)
            bot.register_next_step_handler(message, handle_phone, bot)

def handle_phone(message: types.Message, bot: TeleBot):
    try:
        phone_number = message.contact.phone_number
        if phone_number:
            with Session(engine) as session:
                user = get_user(session, message.chat.id)
                user.phone = str(phone_number)
                user.has_ended = True
                session.commit()
                bot.send_message(message.chat.id, "Вы зарегистрировались в проекте.\n\nПоздравляем с получением бесплатной подписки на 30 суток.Вам Активирован 1 уровень партнерской программы.\n\nПереходите в наш канал: @za_lyubov_igra")
                handle_start_message(bot, message.chat.id, has_new_message=True)
    except:
        if message.text.startswith("8") or message.text.startswith("+7"):
            phone_number = message.text
            if len(phone_number) == 12 or len(phone_number) == 11:
                with Session(engine) as session:
                    user = get_user(session, message.chat.id)
                    user.phone = str(phone_number)
                    user.has_ended = True
                    session.commit()
                    bot.send_message(message.chat.id, "Вы зарегистрировались в проекте.\n\nПоздравляем с получением бесплатной подписки на 30 суток.Вам Активирован 1 уровень партнерской программы.\n\nПереходите в наш канал: @za_lyubov_igra")
                    handle_start_message(bot, message.chat.id, has_new_message=True)
                    return
        bot.send_message(message.chat.id, "Номер телефона не получен")
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reg_button = types.KeyboardButton(text="Отправить номер телефона", 
        request_contact=True)
        keyboard.add(reg_button)
        bot.send_message(message.chat.id, "Подвердите свой номер телефона, нажав кнопку, либо введите другой в формате +7XXXXXXXXXX или 8XXXXXXXXXX", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_phone, bot)
