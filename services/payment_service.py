"""
Сервис для работы с платежами через YooKassa
"""
import uuid
from typing import Dict, Any, Optional
from yookassa import Configuration, Payment
import config


# Инициализация YooKassa
Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_API)


def create_payment(
    amount: int,
    description: str,
    order_number: int,
    return_url: Optional[str] = None,
    receipt_items: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Payment:
    """
    Создает платеж в YooKassa.
    
    Args:
        amount: Сумма платежа в рублях
        description: Описание платежа
        order_number: Номер заказа (ID PayMetadata)
        return_url: URL для возврата после оплаты
        receipt_items: Список товаров для фискального чека
        metadata: Дополнительные метаданные
        
    Returns:
        Объект Payment от YooKassa
    """
    idempotence_key = str(uuid.uuid4())
    return_url = return_url or config.BOT_RETURN_URL
    
    payment_data = {
        "id": idempotence_key,
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": str(description),
        "metadata": {
            "orderNumber": order_number,
            **(metadata or {})
        },
    }
    
    # Добавляем фискальный чек, если указаны товары
    if receipt_items:
        payment_data["receipt"] = {
            "customer": config.RECEIPT_CUSTOMER,
            "items": receipt_items
        }
    
    return Payment.create(payment_data, idempotency_key=idempotence_key)


def create_receipt_item(
    description: str,
    amount: int,
    quantity: str = "1.00",
    vat_code: str = "2",
    payment_mode: str = "full_payment",
    payment_subject: str = "commodity",
    country_code: str = "RU",
    product_code: Optional[str] = None,
    customs_declaration: Optional[str] = None,
    excise: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Создает элемент фискального чека для платежа.
    
    Args:
        description: Описание товара/услуги
        amount: Сумма в рублях
        quantity: Количество
        vat_code: Код НДС
        payment_mode: Режим оплаты
        payment_subject: Предмет расчета
        country_code: Код страны происхождения
        product_code: Код товара
        customs_declaration: Номер таможенной декларации
        excise: Акциз
        
    Returns:
        Словарь с данными товара для чека
    """
    item = {
        "description": description[:128],  # Ограничение YooKassa
        "quantity": quantity,
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "vat_code": vat_code,
        "payment_mode": payment_mode,
        "payment_subject": payment_subject,
        "country_of_origin_code": country_code,
    }
    
    if product_code:
        item["product_code"] = product_code
    if customs_declaration:
        item["customs_declaration_number"] = customs_declaration
    if excise:
        item["excise"] = excise
    
    return item


def get_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает статус платежа по его ID.
    
    Args:
        payment_id: ID платежа в YooKassa
        
    Returns:
        Словарь с информацией о платеже или None
    """
    try:
        payment = Payment.find(payment_id)
        return {
            "id": getattr(payment, "id", None),
            "status": getattr(payment, "status", None),
            "paid": getattr(payment, "paid", False),
            "amount": getattr(payment, "amount", {}).value if hasattr(payment, "amount") and payment.amount else None,
            "metadata": getattr(payment, "metadata", {}),
            "payment_method": getattr(payment, "payment_method", None),
        }
    except Exception as e:
        print(f"[payment] Error getting payment status: {e}")
        return None

