import datetime

import stripe
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from crud import UserCRUD

stripe.api_key = settings.STRIPE_SECRET_KEY

# Список тарифов (создаются один раз в Stripe Dashboard)
price_IDS = {
    "pro_Weekly": "price_1SlCpP060rnebdaLFdX6oyOS",
    "pro_Monthly": "price_1SlCpy060rnebdaLE0uYBaub",
    "pro_Annual": "price_1SlCoD060rnebdaLo510sftI"
}


async def get_user_subscription_price(user):
    if not user.stripe_subscription_id:
        return None

    try:
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

        if subscription.status != "active":
            return None

        # Получаем список items через auto-pagination
        items = subscription['items'].data  # Обращаемся как к словарю

        if not items:
            return None

        # Первый элемент подписки
        item = items[0]

        # Получаем price_id из item
        price_id = item.price.id

        # Получаем объект Price
        price = stripe.Price.retrieve(price_id)

        amount = price.unit_amount / 100
        currency = price.currency.upper()
        interval = price.recurring.interval

        # Форматируем
        if currency == "RUB":
            amount_str = f"{int(amount)} ₽"
        else:
            amount_str = f"{amount:.2f} {currency}"

        print(f"{amount_str} / {interval}")
        return f"{amount_str} / {interval}"

    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return None
    except Exception as e:
        print(f"Error getting subscription price: {e}")
        return None


# Создаём Stripe Customer, если это первая покупка
async def create_or_retrieve_subscription(db: AsyncSession, user):
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email)
        await UserCRUD.update_stripe_customer_id(db, user, customer.id)
        print(f"user {user.email} created stripe_customer_id {customer.id}")
    return user.stripe_customer_id

#Создаём сессию оплаты — пользователь перенаправляется на Stripe Checkout
async def create_session_checkout(db: AsyncSession, user, price_id: str):
    customer_id = await create_or_retrieve_subscription(db, user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode='subscription',
        success_url = "https://psychologyai-production.up.railway.app/payments/success",
        cancel_url = "https://psychologyai-production.up.railway.app/payments/failed"
    )
    return session.url # ссылка, куда редиректим пользователя

#Обрабатываем события от Stripe (самое важное!)
async def handle_webhook_event(event: dict, db: AsyncSession):
    event_type = event.get("type", "unknown")
    print(f"Получено событие Stripe: {event_type}")

    # Безопасно достаём data_object
    data = event.get("data", {})
    data_object = data.get("object", {})

    # Общие проверки
    customer_id = data_object.get("customer")
    if not customer_id:
        print("Нет customer_id")
        return

    user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
    if not user:
        print("Пользователь не найден")
        return

    # 1. Успешная оплата — самый простой вариант
    if event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        subscription_id = data_object.get("subscription")
        if subscription_id:
            # Пытаемся взять период из подписки, но если не получится — берём из инвойса
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                period_end_ts = sub.current_period_end
                period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
                status = sub.status
            except Exception as e:
                print(f"Не удалось взять подписку: {e}")
                # fallback — старое поведение (то, что сейчас хоть что-то записывает)
                period_end_ts = data_object.get("period_end")
                period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
                status = "active"

            print(f"Оплата прошла → {user.email} | period_end: {period_end}")

            await UserCRUD.update_subscription(
                db, user,
                subscription_id=subscription_id,
                status=status,
                period_end=period_end
            )

    # 2. Подписка создана — упрощённо
    elif event_type == "customer.subscription.created":
        subscription_id = data_object.get("id")
        if subscription_id:
            status = data_object.get("status", "unknown")
            period_end_ts = data_object.get("current_period_end")
            period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None

            print(f"Создана подписка → {user.email} | period_end: {period_end}")

            await UserCRUD.update_subscription(
                db, user,
                subscription_id=subscription_id,
                status=status,
                period_end=period_end
            )

    # 3. Обновлена / удалена — минимально
    elif event_type == "customer.subscription.updated":
        subscription_id = data_object.get("id")
        if subscription_id:
            status = data_object.get("status", "unknown")
            period_end_ts = data_object.get("current_period_end")
            period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
            await UserCRUD.update_subscription(db, user, subscription_id, status, period_end)

    elif event_type == "customer.subscription.deleted":
        await UserCRUD.update_subscription(db, user, None, "canceled", None)

    else:
        print(f"Необрабатываемое: {event_type}")