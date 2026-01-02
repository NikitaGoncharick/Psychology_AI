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
    """Обрабатывает входящие webhook-события от Stripe | Синхронизирует статус подписки пользователя в базе данных."""
    event_type = event["type"]
    data_object = event["data"]["object"]
    print(f"Получено событие Stripe: {event_type}")

    customer_id = data_object.get("customer")
    if not customer_id:
        return

    user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
    if not user:
        return

    subscription_id = None

    # Получаем subscription_id разными способами в зависимости от типа события
    if "subscription" in data_object:
        subscription_id = data_object["subscription"]
    elif event_type.startswith("customer.subscription"):
        subscription_id = data_object.get("id")

    # ──────────────────────────────────────────────────────────────
    # 1. Успешная оплата (самый важный кейс для первой оплаты)
    if event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        if not subscription_id:
            print("В invoice нет subscription_id — пропускаем")
            return

        try:
            sub = stripe.Subscription.retrieve(subscription_id)

            status = sub.status
            period_end_ts = sub.current_period_end
            period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None

            print(f"Успешный платёж для {user.email} | "
                  f"Subscription ID: {subscription_id} | "
                  f"Status: {status} | Period end: {period_end}")

            await UserCRUD.update_subscription(
                db, user,
                subscription_id=subscription_id,
                status=status,  # ← важно! берём реальный статус
                period_end=period_end
            )
        except stripe.error.StripeError as e:
            print(f"Ошибка при получении подписки {subscription_id}: {e}")

    # ──────────────────────────────────────────────────────────────
    # 2. Неудачная попытка оплаты
    elif event_type == "invoice.payment_failed":
        if not subscription_id:
            return

        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            status = sub.status or "past_due"
            period_end_ts = sub.current_period_end
            period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None

            print(f"Неудачный платёж для {user.email} | Subscription ID: {subscription_id}")

            await UserCRUD.update_subscription(
                db, user,
                subscription_id=subscription_id,
                status=status,
                period_end=period_end
            )
        except stripe.error.StripeError as e:
            print(f"Ошибка при получении подписки: {e}")

    # ──────────────────────────────────────────────────────────────
    # 3. Подписка отменена
    elif event_type == "customer.subscription.deleted":
        print(f"Подписка отменена для {user.email}")
        await UserCRUD.update_subscription(
            db, user,
            subscription_id=None,
            status="canceled",
            period_end=None
        )

    # ──────────────────────────────────────────────────────────────
    # 4. Подписка создана (очень полезно для триала)
    elif event_type == "customer.subscription.created":
        if not subscription_id:
            return

        status = data_object.get("status", "incomplete")
        period_end_ts = data_object.get("current_period_end")
        period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None

        print(f"Подписка создана для {user.email} | Status: {status} | Period end: {period_end}")

        await UserCRUD.update_subscription(
            db, user,
            subscription_id=subscription_id,
            status=status,
            period_end=period_end
        )

    # ──────────────────────────────────────────────────────────────
    # 5. Подписка обновлена
    elif event_type == "customer.subscription.updated":
        if not subscription_id:
            return

        status = data_object.get("status")
        period_end_ts = data_object.get("current_period_end")
        period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None

        print(f"Подписка обновлена для {user.email} | Новый статус: {status} | Period end: {period_end}")

        await UserCRUD.update_subscription(
            db, user,
            subscription_id=subscription_id,
            status=status,
            period_end=period_end
        )

    else:
        print(f"Необрабатываемое событие: {event_type}")