"""
Главный файл Telegram-бота проекта "За любовь"
"""
from telebot import TeleBot, types
import config
from db.models import init_db
from handlers.start import handle_start_message, handler_start
from handlers.callback import handler_callback
from handlers.subscription_checker import (
    register_manual_handler,   # alias of bind_subscription_commands
    start_subscription_scheduler,  # alias of integrate_subscription_scheduler
    check_and_notify_subscriptions
)
from handlers.db_backup import (
    register_manual_backup_handler,
    start_backup_scheduler,
    trigger_backup_to_chat,
)

# Инициализация бота с токеном из конфигурации
bot = TeleBot(config.TELEGRAM_BOT_TOKEN)

aliases = ["SlashCheckSubs", "check_subs", "checksubs"]

@bot.message_handler(commands=aliases + [a.lower() for a in aliases])
def _cmd(m: types.Message):
    print('start _cmd')
    c3, c1, ce = check_and_notify_subscriptions(bot)
    bot.reply_to(m, f"Проверка выполнена: 3д={c3}, 1д={c1}, истекло={ce}")

# Fallback when the command comes as plain text
@bot.message_handler(func=lambda msg: msg.text.strip().lower() in {
    "/slashchecksubs", "slashchecksubs", "/checksubs", "checksubs", "/check_subs", "check_subs"
})
def _fallback(m: types.Message):
    print('start fallback')
    c3, c1, ce = check_and_notify_subscriptions(bot)
    bot.reply_to(m, f"Проверка выполнена: 3д={c3}, 1д={c1}, истекло={ce}")


@bot.message_handler(commands=['start'])
def start_handler(message: types.Message):
    handler_start(bot, message)

@bot.message_handler(commands=['dev'])
def start_handler(message: types.Message):
    print(message.chat.id, message.message_thread_id)

@bot.message_handler(commands=['backup'])
def backup_handler(message: types.Message):
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    if config.BACKUP_COMMAND_ALLOWED_USER_ID is not None and user_id != config.BACKUP_COMMAND_ALLOWED_USER_ID:
        bot.reply_to(message, "Команда недоступна.")
        return
    trigger_backup_to_chat(bot, message.chat.id)
 
@bot.message_handler(func=lambda message: True)    
def main_message_handler(message):
    if message.text == "На главную": handle_start_message(bot, message.chat.id)
    
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    handler_callback(bot, call)

if __name__ == "__main__":
    # Инициализация базы данных
    init_db()
    
    print("Бот успешно запустился")
    
    # Регистрация команд для проверки подписок
    register_manual_handler(bot)
    
    # Запуск фоновой задачи проверки подписок
    start_subscription_scheduler(bot, config.SUBSCRIPTION_CHECK_INTERVAL)
    
    # Регистрация команд для резервного копирования
    register_manual_backup_handler(bot)
    
    # Автоматическое резервное копирование (закомментировано по умолчанию)
    # start_backup_scheduler(bot, 86400)  # каждые 24 часа
    
    # Запуск бота
    bot.infinity_polling(skip_pending=True)
