# Руководство по миграции на новую архитектуру

Этот документ описывает изменения, внесенные в проект в рамках рефакторинга, и как адаптировать существующий код.

## Основные изменения

### 1. Конфигурация вынесена в `config.py`

**Было:**
```python
bot = TeleBot("7713812500:AAFBkZRpgYKbatoUkj0N-niA-5nXbYWZOJg")
SECRET_API = "live_8sy3urnb4lO3FxsGsaxANT4wC20ZMT97Fb-PAnCD7Sk"
SHOP_ID = 1124758
```

**Стало:**
```python
import config
bot = TeleBot(config.TELEGRAM_BOT_TOKEN)
# Используем config.YOOKASSA_SECRET_API и config.YOOKASSA_SHOP_ID
```

### 2. Создан сервисный слой

Бизнес-логика вынесена в отдельные сервисы:

- `services/payment_service.py` - работа с платежами YooKassa
- `services/referral_service.py` - реферальная система
- `services/subscription_service.py` - управление подписками

**Пример использования:**
```python
from services.payment_service import create_payment
from services.referral_service import distribute_referral_rewards
from services.subscription_service import has_active_subscription

# Создание платежа
payment = create_payment(
    amount=33300,  # в копейках
    description="Подписка на месяц",
    order_number=pay_metadata.id
)

# Проверка подписки
if has_active_subscription(session, user.id):
    # пользователь имеет активную подписку
    pass
```

### 3. Созданы утилиты

Общие функции вынесены в `utils/`:

- `utils/referral.py` - расчеты реферальных бонусов
- `utils/media.py` - отправка медиа-файлов
- `utils/text.py` - работа с текстом

**Пример использования:**
```python
from utils.media import send_media
from utils.referral import get_ref_percent
from utils.text import escape_html

# Отправка медиа
send_media(bot, chat_id, "assets/image.jpg", bot.send_photo, caption="Описание")

# Расчет процента
percent = get_ref_percent(1)  # 40.0 для первой линии

# Экранирование HTML
safe_text = escape_html(user_input)
```

### 4. Обновлена структура handlers

Handlers теперь используют сервисы и утилиты вместо прямой реализации логики.

**Пример рефакторинга handler'а:**

**Было:**
```python
def handler_callback(bot, call):
    # Вся логика внутри функции
    if call.data.startswith("buy-subscribe"):
        # Создание платежа напрямую
        payment = Payment.create({...})
        # Расчет реферальных бонусов
        for i in range(1, 13):
            # сложная логика
```

**Стало:**
```python
from services.payment_service import create_payment
from services.referral_service import distribute_referral_rewards

def handler_callback(bot, call):
    if call.data.startswith("buy-subscribe"):
        # Используем сервис
        payment = create_payment(...)
        # Используем сервис для распределения бонусов
        distribute_referral_rewards(session, user, pay_metadata)
```

## Миграция существующего кода

### Шаг 1: Обновить импорты

Замените прямые импорты на импорты из новых модулей:

```python
# Старый способ
from yookassa import Payment
payment = Payment.create({...})

# Новый способ
from services.payment_service import create_payment
payment = create_payment(...)
```

### Шаг 2: Использовать config вместо хардкода

```python
# Старый способ
ADMIN_CHAT_ID = -1002837224902

# Новый способ
import config
admin_chat_id = config.ADMIN_CHAT_ID
```

### Шаг 3: Вынести бизнес-логику в сервисы

Если в handler'е есть сложная бизнес-логика, вынесите её в соответствующий сервис:

```python
# В handler'е
from services.subscription_service import get_subscription_expiry

expiry = get_subscription_expiry(session, user)
```

### Шаг 4: Использовать утилиты для общих функций

```python
# Старый способ
import html
text = html.escape(user_input)

# Новый способ
from utils.text import escape_html
text = escape_html(user_input)
```

## Обновление checker.py

`checker.py` также должен быть обновлен для использования новой архитектуры:

1. Использовать `config` вместо хардкода
2. Использовать сервисы для работы с платежами и рефералами
3. Использовать модели из `db.models` вместо дублирования

**Пример:**
```python
# Старый способ (в checker.py)
from sqlalchemy import Column, Integer, String, create_engine
# Дублирование моделей

# Новый способ
from db.models import PayMetadata, User, PaymentRecord
from services.referral_service import distribute_referral_rewards
import config
```

## Проверка работоспособности

После миграции проверьте:

1. ✅ Бот запускается без ошибок
2. ✅ Команда `/start` работает
3. ✅ Callback'и обрабатываются корректно
4. ✅ Платежи создаются и обрабатываются
5. ✅ Реферальные бонусы начисляются правильно
6. ✅ Подписки проверяются и продлеваются

## Обратная совместимость

Старый код продолжит работать, но рекомендуется постепенно мигрировать на новую архитектуру:

1. Начните с использования `config` вместо хардкода
2. Постепенно переносите логику в сервисы
3. Используйте утилиты для общих функций
4. Обновляйте handlers по мере необходимости

## Дополнительные улучшения

После базовой миграции можно:

1. Разделить большие handlers на отдельные модули по функциональности
2. Добавить логирование через стандартный модуль `logging`
3. Добавить обработку ошибок через try-except с логированием
4. Добавить unit-тесты для сервисов
5. Оптимизировать запросы к БД

## Вопросы и поддержка

При возникновении проблем при миграции:

1. Проверьте, что все импорты корректны
2. Убедитесь, что `config.py` содержит все необходимые настройки
3. Проверьте, что сервисы и утилиты импортируются правильно
4. Посмотрите примеры использования в документации

