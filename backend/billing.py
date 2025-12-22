import datetime

import stripe
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from crud import UserCRUD, UserCreateSchema, UserLoginSchema, ChatCRUD

stripe.api_key = settings.STRIPE_SECRET_KEY

# Список тарифов (создаются один раз в Stripe Dashboard)
price_IDS = {
    "pro_Weekly": "price_1Sh7tJ060rnebdaLr2Gn7Dxj",
    "pro_Monthly": "price_1Sh7Qf060rnebdaL9coJ2X4v",
    "pro_Annual": "price_1Sh7vU060rnebdaLhbbA3ZGg"
}


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
        success_url = "https://smudgily-imposing-zenobia.ngrok-free.dev/payments/success",
        cancel_url = "https://smudgily-imposing-zenobia.ngrok-free.dev/payments/failed"
    )
    return session.url # ссылка, куда редиректим пользователя

#Обрабатываем события от Stripe (самое важное!)
async def handle_webhook_event(event: dict, db: AsyncSession):
    #Обрабатывает входящие webhook-события от Stripe | Синхронизирует статус подписки пользователя в базе данных.
    event_type = event["type"]
    data_object = event["data"]["object"]
    print(f"Получено событие Stripe: {event_type}")

    # 1. Успешная оплата счёта (invoice paid / payment succeeded)
    if event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        customer_id = data_object.get("customer")
        if not customer_id:
            return
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if not user:
            return

        subscription_id = data_object.get("subscription")  # Может быть None или str
        period_end_ts = data_object.get("period_end")
        period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        print(f"Успешный платёж для {user.email} | Subscription ID: {subscription_id} | Period end: {period_end}")

        await UserCRUD.update_subscription(db, user, subscription_id = subscription_id, status="active", period_end = period_end)

    # 2. Неудачная попытка оплаты счёта
    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        if not customer_id:
            return
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if not user:
            return
        subscription_id = data_object.get("subscription")
        print(f"Неудачный платёж для {user.email} | Subscription ID: {subscription_id}")

        await UserCRUD.update_subscription(db, user, subscription_id = subscription_id, status="past_due", period_end = None)

    # 3. Подписка отменена (пользователь отменил или истёк срок)
    elif event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        if not customer_id:
            return
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if not user:
            return
        print(f"Подписка отменена для {user.email}")

        await UserCRUD.update_subscription(db, user, subscription_id=None, status="canceled", period_end = None)

    # 4. Подписка создана (полезно для триала)
    elif event_type == "customer.subscription.created":
        customer_id = data_object.get("customer")
        if not customer_id:
            return
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if not user:
            return

        subscription_id = data_object["id"]
        status = data_object["status"] # обычно "trialing" или "active"
        period_end_ts = data_object.get("current_period_end")
        period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        print(f"Подписка создана для {user.email} | Status: {status}")

        await UserCRUD.update_subscription(db, user, subscription_id = subscription_id, status = status, period_end = period_end)

    # 5. Подписка обновлена
    elif event_type == "customer.subscription.updated":
        customer_id = data_object.get("customer")
        if not customer_id:
            return
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if not user:
            return
        subscription_id = data_object["id"]
        status = data_object["status"]
        period_end_ts = data_object.get("current_period_end")
        period_end = datetime.datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        print(f"Подписка обновлена для {user.email} | Новый статус: {status}")

        await UserCRUD.update_subscription(db, user, subscription_id = subscription_id, status = status, period_end = period_end)

    else:
        print(f"Необрабатываемое событие: {event_type}")