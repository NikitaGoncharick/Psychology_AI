from fastapi import Request
from fastapi.responses import HTMLResponse
from crud import UserCRUD, ChatCRUD
import billing

async def get_profile_data(request, db, user_data):
    user_email = user_data.email
    subscription_status = user_data.subscription_status
    # if subscription_status == "active":
    #     period_end = user_data.subscription_current_period_end

    return {
        "user_email": user_email,
        "subscription_status": subscription_status,
        "subscription_price": await billing.get_user_subscription_price(user_data),
        "period_end": (user_data.subscription_current_period_end.strftime("%d %B %Y")
        if user_data.subscription_current_period_end
        else None)
    }


    print(f"user_email: {user_email}, subscription_status: {subscription_status}")