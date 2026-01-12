# Stripe Subscription Management System Setup

This document provides complete setup instructions for the LetsGoal Stripe subscription management system.

## Overview

The system includes:
- **5 Database Models**: Plan, StripeCustomer, Subscription, SubscriptionHistory, Invoice
- **Complete Stripe Service**: Customer creation, subscription management, webhook handling
- **25+ Admin Endpoints**: Plan management, subscription CRUD, billing history, revenue analytics
- **3 Default Plans**: Free ($0), Pro ($9.99), Business ($19.99)
- **Secure Webhooks**: Signature verification and event processing
- **Migration System**: Easy setup and rollback capabilities

## Prerequisites

1. **Stripe Account**: Create a Stripe account at https://stripe.com
2. **API Keys**: Get your Stripe API keys from the Stripe Dashboard
3. **Webhook Endpoint**: Configure webhook in Stripe to point to your server

## Installation Steps

### 1. Install Dependencies

The Stripe dependency has been added to `requirements.txt`. Install it:

```bash
pip install -r backend/requirements.txt
```

### 2. Environment Configuration

Add these environment variables to your `.env` file or system environment:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_51...  # Your Stripe Secret Key
STRIPE_PUBLISHABLE_KEY=pk_test_51...  # Your Stripe Publishable Key
STRIPE_WEBHOOK_SECRET=whsec_...  # Your Webhook Endpoint Secret
```

### 3. Run Database Migration

Execute the migration script to create subscription tables and default plans:

```bash
cd backend/migrations
python add_stripe_subscription_system.py migrate
```

Check migration status:
```bash
python add_stripe_subscription_system.py status
```

### 4. Configure Stripe Webhook

1. Go to your Stripe Dashboard → Developers → Webhooks
2. Create a new webhook endpoint pointing to: `https://yourdomain.com/api/admin/webhooks/stripe`
3. Select these events to listen for:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.created`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook secret and set it as `STRIPE_WEBHOOK_SECRET`

### 5. Create Real Stripe Plans

The migration creates placeholder plans. You need to create actual plans in Stripe:

1. Go to Stripe Dashboard → Products
2. Create three products with pricing:
   - **Free Plan**: $0/month
   - **Pro Plan**: $9.99/month  
   - **Business Plan**: $19.99/month
3. Copy the Price IDs (they start with `price_`)
4. Update the plans in your admin panel with the real Stripe Price IDs

## API Endpoints

### Plan Management
- `GET /api/admin/plans` - List all plans
- `POST /api/admin/plans` - Create new plan
- `PUT /api/admin/plans/{id}` - Update plan
- `DELETE /api/admin/plans/{id}` - Archive plan

### Subscription Management
- `GET /api/admin/subscriptions` - List subscriptions (with filtering)
- `POST /api/admin/subscriptions` - Create subscription for user
- `GET /api/admin/subscriptions/{id}` - Get subscription details
- `PUT /api/admin/subscriptions/{id}` - Update subscription (change plan)
- `POST /api/admin/subscriptions/{id}/cancel` - Cancel subscription
- `POST /api/admin/subscriptions/{id}/reactivate` - Reactivate subscription

### Invoice Management
- `GET /api/admin/invoices` - List invoices (with filtering)
- `GET /api/admin/invoices/{id}` - Get invoice details

### Analytics & Statistics
- `GET /api/admin/subscriptions/stats/overview` - Subscription overview (MRR, ARR, churn)
- `GET /api/admin/subscriptions/stats/revenue` - Revenue analytics by date/plan

### Webhook Handler
- `POST /api/admin/webhooks/stripe` - Stripe webhook endpoint (automatically processes events)

## Default Plans Features

### Free Plan ($0/month)
- 5 goals maximum
- 10 subgoals per goal
- Basic goal tracking
- No sharing capabilities

### Pro Plan ($9.99/month)
- 50 goals maximum
- 50 subgoals per goal
- Goal sharing with others
- Advanced analytics
- Data export
- Custom themes
- Collaboration tools
- Reminder notifications

### Business Plan ($19.99/month)
- Unlimited goals and subgoals
- All Pro features plus:
- Priority support
- API access
- Team management
- Advanced reporting
- White label options
- SLA guarantee

## Usage Examples

### Create a Subscription (Admin)

```bash
curl -X POST https://yourdomain.com/api/admin/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "plan_id": 2,
    "trial_days": 14
  }'
```

### Get Subscription Statistics

```bash
curl https://yourdomain.com/api/admin/subscriptions/stats/overview
```

### Cancel Subscription

```bash
curl -X POST https://yourdomain.com/api/admin/subscriptions/456/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "at_period_end": true,
    "reason": "User requested cancellation"
  }'
```

## Security Features

- **Webhook Signature Verification**: All webhook events are verified using HMAC-SHA256
- **Admin Authentication**: All endpoints require admin privileges
- **SQL Injection Protection**: Uses SQLAlchemy ORM with parameterized queries
- **Input Validation**: Comprehensive validation on all endpoints
- **Error Handling**: Proper error responses without sensitive data exposure

## Monitoring & Logging

The system includes comprehensive logging for:
- Subscription lifecycle events
- Payment processing
- Webhook event handling
- Error tracking
- Revenue analytics

## Troubleshooting

### Common Issues

1. **Webhook Authentication Failed**
   - Verify `STRIPE_WEBHOOK_SECRET` is correct
   - Check webhook endpoint URL in Stripe Dashboard

2. **Subscription Creation Fails**
   - Verify Stripe API keys are valid
   - Check that the plan's `stripe_plan_id` matches a real Stripe Price ID

3. **Migration Fails**
   - Ensure database is writable
   - Check for conflicting table names
   - Run `python add_stripe_subscription_system.py status` to check current state

### Debug Mode

Set Flask to debug mode to see detailed error messages:
```bash
export FLASK_DEBUG=1
```

### Check Stripe Logs

Monitor Stripe Dashboard → Developers → Logs for API call details and errors.

## Rollback Instructions

If you need to remove the subscription system:

```bash
cd backend/migrations
python add_stripe_subscription_system.py rollback
```

⚠️ **WARNING**: This will delete ALL subscription data permanently!

## Support

For issues related to:
- **Stripe Integration**: Check Stripe Dashboard logs and documentation
- **Database Issues**: Verify migration status and check SQLite database
- **API Endpoints**: Review admin.py for endpoint implementations
- **Webhook Processing**: Check application logs for webhook event handling

## Security Checklist

Before going to production:

- [ ] Replace test Stripe keys with live keys
- [ ] Enable HTTPS for webhook endpoint
- [ ] Set strong webhook secret
- [ ] Review and test all webhook events
- [ ] Set up monitoring for failed payments
- [ ] Configure backup system for subscription data
- [ ] Test subscription cancellation and reactivation flows
- [ ] Verify PCI compliance requirements
- [ ] Set up proper logging and alerting

## Next Steps

1. Customize plan features based on your application needs
2. Implement frontend subscription management UI
3. Add email notifications for subscription events
4. Set up automated dunning management for failed payments
5. Implement usage-based billing if needed
6. Add subscription analytics dashboard
7. Configure automated invoice generation and delivery