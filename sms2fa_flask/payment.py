from . import app
import stripe
from stripe.error import InvalidRequestError
stripe.api_key = app.config['STRIPE_SECRET_KEY']

def create_stripe_customer(email, token_id):
    try:
        customer = stripe.Customer.create(
                    email=email,
                    source=token_id
                    )
        return customer.id
    except InvalidRequestError as e:
        return None

def update_stripe_customer(customer_id, token_id):
    try:
        stripe.Customer.modify(customer_id, source=token_id)
        return True
    except InvalidRequestError as e:
        return False