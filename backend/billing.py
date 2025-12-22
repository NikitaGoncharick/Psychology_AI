import stripe
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from models import User

stripe.api_key = settings.STRIPE_SECRET_KEY

# Список тарифов (создаются один раз в Stripe Dashboard)
price_IDS = {
    "pro_Weekly": "prod_TeQkPWqOIA6wjp",
    "pro_Monthly": "prod_TeQHtkpUYA2Y7w",
    "pro_Annual": "prod_TeQnt32K9QUszs"
}

async def create_or_retrieve_subscription(db: AsyncSession, user: User):
    print(f"Creating subscription for {user.email}, user_id={user.id}")