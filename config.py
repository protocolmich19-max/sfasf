"""
Конфигурация проекта "За любовь"
Все настройки вынесены в отдельный модуль для удобства управления
"""
import os
from typing import Optional

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7713812500:AAFBkZRpgYKbatoUkj0N-niA-5nXbYWZOJg")
BOT_RETURN_URL = "https://t.me/forlove2025_bot"

# YooKassa Payment Configuration
YOOKASSA_SHOP_ID = 1124758
YOOKASSA_SECRET_API = os.getenv("YOOKASSA_SECRET_API", "live_8sy3urnb4lO3FxsGsaxANT4wC20ZMT97Fb-PAnCD7Sk")
YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"

# Database Configuration
DB_CONNECTION_STRING = os.getenv(
    "DB_CONNECTION_STRING",
    "mysql+pymysql://gen_user:hamsterdev1@89.169.45.136:3306/default_db"
)

# Admin Configuration
ADMIN_ACCOUNT = 6062822304
ADMIN_CHAT_ID = -1002837224902
ADMIN_EDUCATION_THREAD_ID: Optional[int] = None

# Backup Configuration
BACKUP_DIR = "backups"
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./google_disk_key.json")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "19ieR8xgmDI1tmqrrwH2_igQaC1pU5vYX")
GDRIVE_DELEGATED_USER = os.getenv("GDRIVE_DELEGATED_USER", os.getenv("GOOGLE_DELEGATED_USER_EMAIL", "")).strip()

_backup_admin_id_raw = os.getenv("BACKUP_ADMIN_TG_ID", "6742056004").strip()
BACKUP_COMMAND_ALLOWED_USER_ID: Optional[int] = int(_backup_admin_id_raw) if _backup_admin_id_raw else None

# Subscription Configuration
SUBSCRIPTION_CHECK_INTERVAL = 3600  # секунды
AUTOPAY_RETRY_SECONDS = 3600
AUTOPAY_DEFAULT_AMOUNT = 333

# Payment Receipt Configuration (для фискальных чеков)
RECEIPT_CUSTOMER = {
    "full_name": "Николаев Артем Алексеевич",
    "email": "cfznyjdf13@mail.ru",
    "phone": "79166758299",
    "inn": "170108382176"
}

RECEIPT_PRODUCT_CODE = "44 4D 01 00 21 FA 41 00 23 05 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 12 00 AB 00"
RECEIPT_CUSTOMS_DECLARATION = "10714040/140917/0090376"

# Project Paths
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# External Links
TELEGRAM_CHANNEL = "https://t.me/za_lyubov_igra"
RUTUBE_CHANNEL = "https://rutube.ru/channel/25861872"
LEADERS_CHANNEL = "https://t.me/+1-Vj-ec0BOw1NTYy"

# Support Contacts
SUPPORT_CONTACT = "@RodionRa"
TECH_SUPPORT_CONTACT = "@RodionRa"
EDUCATION_CONTACT = "@irrrun"

