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
        success_url = "https://psychology.ai/success",
        cancel_url = "https://psychology.ai/cancel"
    )
    return session.url # ссылка, куда редиректим пользователя

#Обрабатываем события от Stripe (самое важное!)
async def handle_webhook_event(event: dict, db: AsyncSession):
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type in ["invoice.paid", "invoice.payment_succeeded"]:
        customer_id = data["customer"]
        user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
        if user:
            print("Платёж Успешно Прошёл")
            await UserCRUD.update_subscription(db, user,
                                               subscription_id=data["subscription"],
                                               status="active",
                                               period_end = datetime.fromtimestamp(data["period_end"]))

        # Платёж не прошёл — помечаем как past_due
        elif event_type == "invoice.payment_failed":
            customer_id = data["customer"]
            user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
            if user:
                print("Платёж не прошёл")
                await UserCRUD.update_subscription(db, user, data["subscription"], "past_due", None)

        # Подписка отменена
        elif event_type == "customer.subscription.deleted":
            customer_id = data["customer"]
            user = await UserCRUD.get_by_stripe_customer_id(db, customer_id)
            if user:
                print("Подписка отменена")
                await UserCRUD.update_subscription(db, user,None, "canceled", None)