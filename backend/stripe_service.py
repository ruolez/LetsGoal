import os
import sys
sys.path.append('/app')
import stripe
from datetime import datetime, timedelta
from flask import current_app
from backend.models import db, User, Plan, StripeCustomer, Subscription, SubscriptionHistory, Invoice
import logging
import hashlib
import hmac
import json

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class StripeService:
    """Service class for Stripe subscription management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def verify_webhook_signature(self, payload, signature, webhook_secret):
        """Verify Stripe webhook signature for security"""
        try:
            computed_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Extract signature from header
            signature_elements = signature.split(',')
            signature_dict = {}
            for element in signature_elements:
                key, value = element.split('=')
                signature_dict[key] = value
            
            received_signature = signature_dict.get('v1')
            
            # Secure comparison
            return hmac.compare_digest(computed_signature, received_signature)
            
        except Exception as e:
            self.logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def create_or_get_customer(self, user_id):
        """Create or retrieve Stripe customer for user"""
        try:
            # Check if customer already exists
            stripe_customer = StripeCustomer.query.filter_by(user_id=user_id).first()
            if stripe_customer:
                # Verify customer exists in Stripe
                try:
                    customer = stripe.Customer.retrieve(stripe_customer.stripe_customer_id)
                    return {'success': True, 'customer': customer, 'stripe_customer': stripe_customer}
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist in Stripe, create new one
                    pass
            
            # Get user details
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Create customer in Stripe
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={
                    'user_id': str(user.id),
                    'letsgoal_user': 'true'
                }
            )
            
            # Save customer to database
            if stripe_customer:
                stripe_customer.stripe_customer_id = customer.id
            else:
                stripe_customer = StripeCustomer(
                    user_id=user_id,
                    stripe_customer_id=customer.id
                )
                db.session.add(stripe_customer)
            
            db.session.commit()
            
            return {'success': True, 'customer': customer, 'stripe_customer': stripe_customer}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create/get customer for user {user_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_subscription(self, user_id, plan_id, payment_method_id=None, trial_days=None):
        """Create a new subscription for user"""
        try:
            # Get plan
            plan = Plan.query.get(plan_id)
            if not plan or not plan.active:
                return {'success': False, 'error': 'Invalid or inactive plan'}
            
            # Get or create customer
            customer_result = self.create_or_get_customer(user_id)
            if not customer_result['success']:
                return customer_result
            
            customer = customer_result['customer']
            
            # Prepare subscription parameters
            subscription_params = {
                'customer': customer.id,
                'items': [{'price': plan.stripe_plan_id}],
                'metadata': {
                    'user_id': str(user_id),
                    'plan_id': str(plan_id),
                    'letsgoal_subscription': 'true'
                }
            }
            
            # Add payment method if provided
            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id
            
            # Add trial period if specified
            if trial_days:
                trial_end = datetime.utcnow() + timedelta(days=trial_days)
                subscription_params['trial_end'] = int(trial_end.timestamp())
            
            # Create subscription in Stripe
            stripe_subscription = stripe.Subscription.create(**subscription_params)
            
            # Save subscription to database
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                stripe_subscription_id=stripe_subscription.id,
                status=stripe_subscription.status,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                trial_start=datetime.fromtimestamp(stripe_subscription.trial_start) if stripe_subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None
            )
            subscription.set_metadata(stripe_subscription.metadata)
            
            db.session.add(subscription)
            
            # Create history record
            history = SubscriptionHistory(
                subscription_id=subscription.id,
                action='created',
                new_plan_id=plan_id,
                new_status=stripe_subscription.status,
                change_reason='New subscription created'
            )
            db.session.add(history)
            
            db.session.commit()
            
            return {
                'success': True, 
                'subscription': stripe_subscription,
                'local_subscription': subscription
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_subscription(self, subscription_id, new_plan_id=None, prorate=True):
        """Update subscription to new plan"""
        try:
            # Get local subscription
            subscription = Subscription.query.get(subscription_id)
            if not subscription:
                return {'success': False, 'error': 'Subscription not found'}
            
            # Get Stripe subscription
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            
            update_params = {}
            old_plan_id = subscription.plan_id
            
            if new_plan_id:
                new_plan = Plan.query.get(new_plan_id)
                if not new_plan or not new_plan.active:
                    return {'success': False, 'error': 'Invalid or inactive plan'}
                
                # Update subscription items
                update_params['items'] = [{
                    'id': stripe_subscription['items']['data'][0]['id'],
                    'price': new_plan.stripe_plan_id
                }]
                update_params['proration_behavior'] = 'create_prorations' if prorate else 'none'
            
            # Update in Stripe
            updated_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                **update_params
            )
            
            # Update local subscription
            if new_plan_id:
                subscription.plan_id = new_plan_id
            subscription.status = updated_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(updated_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(updated_subscription.current_period_end)
            subscription.set_metadata(updated_subscription.metadata)
            
            # Create history record
            history = SubscriptionHistory(
                subscription_id=subscription.id,
                action='plan_changed' if new_plan_id else 'updated',
                old_plan_id=old_plan_id,
                new_plan_id=new_plan_id or subscription.plan_id,
                old_status=subscription.status,
                new_status=updated_subscription.status,
                change_reason='Plan updated via admin'
            )
            db.session.add(history)
            
            db.session.commit()
            
            return {
                'success': True,
                'subscription': updated_subscription,
                'local_subscription': subscription
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cancel_subscription(self, subscription_id, at_period_end=True, reason=None):
        """Cancel a subscription"""
        try:
            # Get local subscription
            subscription = Subscription.query.get(subscription_id)
            if not subscription:
                return {'success': False, 'error': 'Subscription not found'}
            
            # Cancel in Stripe
            if at_period_end:
                # Cancel at end of billing period
                updated_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # Cancel immediately
                updated_subscription = stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
            
            # Update local subscription
            subscription.status = updated_subscription.status
            if updated_subscription.get('canceled_at'):
                subscription.canceled_at = datetime.fromtimestamp(updated_subscription.canceled_at)
            if updated_subscription.get('ended_at'):
                subscription.ended_at = datetime.fromtimestamp(updated_subscription.ended_at)
            
            # Create history record
            history = SubscriptionHistory(
                subscription_id=subscription.id,
                action='canceled',
                old_status=subscription.status,
                new_status=updated_subscription.status,
                change_reason=reason or ('Canceled at period end' if at_period_end else 'Canceled immediately')
            )
            db.session.add(history)
            
            db.session.commit()
            
            return {
                'success': True,
                'subscription': updated_subscription,
                'local_subscription': subscription
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to cancel subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reactivate_subscription(self, subscription_id, plan_id):
        """Reactivate a canceled subscription"""
        try:
            # Get local subscription
            subscription = Subscription.query.get(subscription_id)
            if not subscription:
                return {'success': False, 'error': 'Subscription not found'}
            
            # Get plan
            plan = Plan.query.get(plan_id)
            if not plan or not plan.active:
                return {'success': False, 'error': 'Invalid or inactive plan'}
            
            # Create new subscription in Stripe (can't reactivate deleted ones)
            customer_result = self.create_or_get_customer(subscription.user_id)
            if not customer_result['success']:
                return customer_result
            
            customer = customer_result['customer']
            
            # Create new subscription
            new_stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': plan.stripe_plan_id}],
                metadata={
                    'user_id': str(subscription.user_id),
                    'plan_id': str(plan_id),
                    'letsgoal_subscription': 'true',
                    'reactivated_from': subscription.stripe_subscription_id
                }
            )
            
            # Update local subscription
            subscription.stripe_subscription_id = new_stripe_subscription.id
            subscription.plan_id = plan_id
            subscription.status = new_stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(new_stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(new_stripe_subscription.current_period_end)
            subscription.canceled_at = None
            subscription.ended_at = None
            subscription.set_metadata(new_stripe_subscription.metadata)
            
            # Create history record
            history = SubscriptionHistory(
                subscription_id=subscription.id,
                action='reactivated',
                new_plan_id=plan_id,
                new_status=new_stripe_subscription.status,
                change_reason='Subscription reactivated'
            )
            db.session.add(history)
            
            db.session.commit()
            
            return {
                'success': True,
                'subscription': new_stripe_subscription,
                'local_subscription': subscription
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to reactivate subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def sync_subscription_from_stripe(self, stripe_subscription_id):
        """Sync subscription data from Stripe to local database"""
        try:
            # Get subscription from Stripe
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            
            # Find local subscription
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=stripe_subscription_id
            ).first()
            
            if not subscription:
                return {'success': False, 'error': 'Local subscription not found'}
            
            # Update local subscription
            old_status = subscription.status
            subscription.status = stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            if stripe_subscription.trial_start:
                subscription.trial_start = datetime.fromtimestamp(stripe_subscription.trial_start)
            if stripe_subscription.trial_end:
                subscription.trial_end = datetime.fromtimestamp(stripe_subscription.trial_end)
            if stripe_subscription.canceled_at:
                subscription.canceled_at = datetime.fromtimestamp(stripe_subscription.canceled_at)
            if stripe_subscription.ended_at:
                subscription.ended_at = datetime.fromtimestamp(stripe_subscription.ended_at)
            
            subscription.set_metadata(stripe_subscription.metadata)
            
            # Create history record if status changed
            if old_status != subscription.status:
                history = SubscriptionHistory(
                    subscription_id=subscription.id,
                    action='synced',
                    old_status=old_status,
                    new_status=subscription.status,
                    change_reason='Synced from Stripe webhook'
                )
                db.session.add(history)
            
            db.session.commit()
            
            return {'success': True, 'subscription': subscription}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to sync subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def sync_invoice_from_stripe(self, stripe_invoice_id):
        """Sync invoice data from Stripe to local database"""
        try:
            # Get invoice from Stripe
            stripe_invoice = stripe.Invoice.retrieve(stripe_invoice_id)
            
            # Find subscription
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=stripe_invoice.subscription
            ).first()
            
            if not subscription:
                self.logger.warning(f"Subscription not found for invoice {stripe_invoice_id}")
                return {'success': False, 'error': 'Subscription not found'}
            
            # Check if invoice already exists
            invoice = Invoice.query.filter_by(
                stripe_invoice_id=stripe_invoice_id
            ).first()
            
            if not invoice:
                invoice = Invoice(
                    subscription_id=subscription.id,
                    stripe_invoice_id=stripe_invoice_id
                )
                db.session.add(invoice)
            
            # Update invoice data
            invoice.amount_due = stripe_invoice.amount_due / 100  # Convert from cents
            invoice.amount_paid = stripe_invoice.amount_paid / 100
            invoice.amount_remaining = stripe_invoice.amount_remaining / 100
            invoice.currency = stripe_invoice.currency.upper()
            invoice.status = stripe_invoice.status
            invoice.paid = stripe_invoice.paid
            invoice.payment_intent_id = stripe_invoice.payment_intent
            invoice.invoice_pdf = stripe_invoice.invoice_pdf
            invoice.hosted_invoice_url = stripe_invoice.hosted_invoice_url
            
            if stripe_invoice.lines.data:
                line = stripe_invoice.lines.data[0]
                if line.period:
                    invoice.period_start = datetime.fromtimestamp(line.period.start)
                    invoice.period_end = datetime.fromtimestamp(line.period.end)
            
            if stripe_invoice.due_date:
                invoice.due_date = datetime.fromtimestamp(stripe_invoice.due_date)
            if stripe_invoice.status_transitions.paid_at:
                invoice.paid_at = datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at)
            
            invoice.set_metadata(stripe_invoice.metadata)
            
            db.session.commit()
            
            return {'success': True, 'invoice': invoice}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to sync invoice: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_plan(self, name, price, currency='USD', interval='month', features=None):
        """Create a new subscription plan in Stripe and database"""
        try:
            # Create price in Stripe
            stripe_price = stripe.Price.create(
                unit_amount=int(price * 100),  # Convert to cents
                currency=currency.lower(),
                recurring={'interval': interval},
                product_data={
                    'name': name,
                    'metadata': {
                        'letsgoal_plan': 'true'
                    }
                }
            )
            
            # Save plan to database
            plan = Plan(
                name=name,
                stripe_plan_id=stripe_price.id,
                price=price,
                currency=currency.upper(),
                interval=interval
            )
            
            if features:
                plan.set_features(features)
            
            db.session.add(plan)
            db.session.commit()
            
            return {'success': True, 'plan': plan, 'stripe_price': stripe_price}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create plan: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_plan(self, plan_id, name=None, features=None, active=None):
        """Update a plan (limited fields can be updated in Stripe)"""
        try:
            plan = Plan.query.get(plan_id)
            if not plan:
                return {'success': False, 'error': 'Plan not found'}
            
            # Update in Stripe (limited options)
            if name:
                stripe.Product.modify(
                    plan.stripe_plan_id,
                    name=name
                )
                plan.name = name
            
            # Update local plan
            if features is not None:
                plan.set_features(features)
            if active is not None:
                plan.active = active
            
            db.session.commit()
            
            return {'success': True, 'plan': plan}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update plan: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_webhook_event(self, event_type, event_data):
        """Handle Stripe webhook events"""
        try:
            if event_type == 'customer.subscription.updated':
                return self.sync_subscription_from_stripe(event_data['object']['id'])
            
            elif event_type == 'customer.subscription.deleted':
                return self.sync_subscription_from_stripe(event_data['object']['id'])
            
            elif event_type == 'invoice.payment_succeeded':
                return self.sync_invoice_from_stripe(event_data['object']['id'])
            
            elif event_type == 'invoice.payment_failed':
                return self.sync_invoice_from_stripe(event_data['object']['id'])
            
            elif event_type == 'invoice.created':
                return self.sync_invoice_from_stripe(event_data['object']['id'])
            
            else:
                self.logger.info(f"Unhandled webhook event: {event_type}")
                return {'success': True, 'message': 'Event not handled'}
                
        except Exception as e:
            self.logger.error(f"Failed to handle webhook event {event_type}: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global service instance
stripe_service = StripeService()