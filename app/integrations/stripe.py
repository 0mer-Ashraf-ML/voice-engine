import stripe
from typing import Dict, Any, List, Optional
from app.config import settings

class StripeIntegration:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    def create_customer(
        self,
        email: str,
        name: str,
        organization_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            customer_metadata = {
                "organization_id": organization_id
            }
            if metadata:
                customer_metadata.update(metadata)
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            return {
                "success": True,
                "customer_id": customer.id,
                "customer": customer
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Customer creation failed: {str(e)}"}
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "payment_settings": {"save_default_payment_method": "on_subscription"},
                "expand": ["latest_invoice.payment_intent"]
            }
            
            if trial_period_days:
                subscription_data["trial_period_days"] = trial_period_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            return {
                "success": True,
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "subscription": subscription
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Subscription creation failed: {str(e)}"}
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            
            return {
                "success": True,
                "subscription": subscription
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Subscription cancellation failed: {str(e)}"}
    
    def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            usage_record_data = {
                "quantity": quantity,
                "action": "increment"
            }
            
            if timestamp:
                usage_record_data["timestamp"] = timestamp
            
            usage_record = stripe.UsageRecord.create(
                subscription_item=subscription_item_id,
                **usage_record_data
            )
            
            return {
                "success": True,
                "usage_record": usage_record
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Usage record creation failed: {str(e)}"}
    
    def create_invoice_item(
        self,
        customer_id: str,
        amount: int,  # Amount in cents
        currency: str = "usd",
        description: str = "Usage charges"
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            invoice_item = stripe.InvoiceItem.create(
                customer=customer_id,
                amount=amount,
                currency=currency,
                description=description
            )
            
            return {
                "success": True,
                "invoice_item": invoice_item
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Invoice item creation failed: {str(e)}"}
    
    def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool = True
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=auto_advance
            )
            
            # Finalize the invoice
            if auto_advance:
                invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            return {
                "success": True,
                "invoice": invoice
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Invoice creation failed: {str(e)}"}
    
    def retrieve_customer(self, customer_id: str) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            customer = stripe.Customer.retrieve(customer_id)
            
            return {
                "success": True,
                "customer": customer
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Customer retrieval failed: {str(e)}"}
    
    def list_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            
            return {
                "success": True,
                "invoices": invoices.data
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Invoice listing failed: {str(e)}"}
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        if not self.webhook_secret:
            return {"error": "Stripe webhook secret not configured"}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            return {
                "success": True,
                "event": event
            }
            
        except ValueError:
            return {"error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"error": "Invalid signature"}
        except Exception as e:
            return {"error": f"Webhook verification failed: {str(e)}"}
    
    def create_payment_intent(
        self,
        amount: int,  # Amount in cents
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        if not stripe.api_key:
            return {"error": "Stripe API key not configured"}
        
        try:
            payment_intent_data = {
                "amount": amount,
                "currency": currency,
                "automatic_payment_methods": {"enabled": True}
            }
            
            if customer_id:
                payment_intent_data["customer"] = customer_id
            
            if metadata:
                payment_intent_data["metadata"] = metadata
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            return {
                "success": True,
                "client_secret": payment_intent.client_secret,
                "payment_intent": payment_intent
            }
            
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"error": f"Payment intent creation failed: {str(e)}"}
    
    def get_pricing_plans(self) -> List[Dict[str, Any]]:
        """Return predefined pricing plans"""
        return [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "currency": "usd",
                "interval": "month",
                "features": [
                    "100 minutes/month",
                    "1 assistant",
                    "Basic support"
                ],
                "limits": {
                    "minutes": 100,
                    "assistants": 1,
                    "phone_numbers": 0
                }
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 2900,  # $29.00
                "currency": "usd",
                "interval": "month",
                "stripe_price_id": "price_pro_monthly",
                "features": [
                    "1000 minutes/month", 
                    "10 assistants",
                    "5 phone numbers",
                    "Priority support"
                ],
                "limits": {
                    "minutes": 1000,
                    "assistants": 10,
                    "phone_numbers": 5
                }
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 9900,  # $99.00
                "currency": "usd",
                "interval": "month",
                "stripe_price_id": "price_enterprise_monthly",
                "features": [
                    "Unlimited minutes",
                    "Unlimited assistants",
                    "Unlimited phone numbers",
                    "24/7 support",
                    "Custom integrations"
                ],
                "limits": {
                    "minutes": -1,  # Unlimited
                    "assistants": -1,
                    "phone_numbers": -1
                }
            }
        ]