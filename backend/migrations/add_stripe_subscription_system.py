#!/usr/bin/env python3
"""
Migration script to add Stripe subscription system tables and default plans
Run this script to create the subscription management tables and populate with default plans
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Plan
from app import create_app
from datetime import datetime

def run_migration():
    """Run the subscription system migration"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting Stripe subscription system migration...")
        
        try:
            # Create all tables (this will create the new subscription tables)
            db.create_all()
            print("✅ Created subscription tables: plans, stripe_customers, subscriptions, subscription_history, invoices")
            
            # Check if default plans already exist
            existing_plans = Plan.query.count()
            if existing_plans > 0:
                print(f"⚠️  Found {existing_plans} existing plans, skipping default plan creation")
                return
            
            # Create default subscription plans
            default_plans = [
                {
                    'name': 'Free Plan',
                    'stripe_plan_id': 'price_free',  # This would be replaced with actual Stripe price ID
                    'price': 0.00,
                    'currency': 'USD',
                    'interval': 'month',
                    'features': {
                        'max_goals': 5,
                        'max_subgoals_per_goal': 10,
                        'goal_sharing': False,
                        'advanced_analytics': False,
                        'priority_support': False,
                        'export_data': False,
                        'custom_themes': False,
                        'api_access': False
                    },
                    'active': True
                },
                {
                    'name': 'Pro Plan',
                    'stripe_plan_id': 'price_pro_monthly',  # This would be replaced with actual Stripe price ID
                    'price': 9.99,
                    'currency': 'USD',
                    'interval': 'month',
                    'features': {
                        'max_goals': 50,
                        'max_subgoals_per_goal': 50,
                        'goal_sharing': True,
                        'advanced_analytics': True,
                        'priority_support': False,
                        'export_data': True,
                        'custom_themes': True,
                        'api_access': False,
                        'collaboration_tools': True,
                        'reminder_notifications': True
                    },
                    'active': True
                },
                {
                    'name': 'Business Plan',
                    'stripe_plan_id': 'price_business_monthly',  # This would be replaced with actual Stripe price ID
                    'price': 19.99,
                    'currency': 'USD',
                    'interval': 'month',
                    'features': {
                        'max_goals': 'unlimited',
                        'max_subgoals_per_goal': 'unlimited',
                        'goal_sharing': True,
                        'advanced_analytics': True,
                        'priority_support': True,
                        'export_data': True,
                        'custom_themes': True,
                        'api_access': True,
                        'collaboration_tools': True,
                        'reminder_notifications': True,
                        'team_management': True,
                        'advanced_reporting': True,
                        'white_label': True,
                        'sla_guarantee': True
                    },
                    'active': True
                }
            ]
            
            # Create the plans
            created_plans = []
            for plan_data in default_plans:
                plan = Plan(
                    name=plan_data['name'],
                    stripe_plan_id=plan_data['stripe_plan_id'],
                    price=plan_data['price'],
                    currency=plan_data['currency'],
                    interval=plan_data['interval'],
                    active=plan_data['active']
                )
                plan.set_features(plan_data['features'])
                
                db.session.add(plan)
                created_plans.append(plan_data['name'])
            
            # Commit the changes
            db.session.commit()
            
            print(f"✅ Created {len(created_plans)} default subscription plans:")
            for plan_name in created_plans:
                print(f"   • {plan_name}")
            
            print("\n📋 Plan Features Summary:")
            print("   Free Plan: 5 goals, 10 subgoals per goal, basic features")
            print("   Pro Plan: 50 goals, 50 subgoals per goal, sharing & analytics")
            print("   Business Plan: Unlimited goals, all features, priority support")
            
            print("\n⚠️  IMPORTANT SETUP NOTES:")
            print("1. Replace placeholder stripe_plan_id values with actual Stripe Price IDs")
            print("2. Set STRIPE_SECRET_KEY environment variable")
            print("3. Set STRIPE_WEBHOOK_SECRET environment variable for webhook security")
            print("4. Configure webhook endpoint: /api/admin/webhooks/stripe")
            print("5. Update plan features as needed through the admin interface")
            
            print("\n🎉 Stripe subscription system migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            sys.exit(1)

def rollback_migration():
    """Rollback the subscription system migration (WARNING: This will delete all subscription data!)"""
    app = create_app()
    
    with app.app_context():
        print("⚠️  WARNING: This will delete ALL subscription data!")
        confirmation = input("Type 'CONFIRM_ROLLBACK' to proceed: ")
        
        if confirmation != 'CONFIRM_ROLLBACK':
            print("❌ Rollback canceled")
            return
        
        try:
            # Drop subscription tables
            db.session.execute('DROP TABLE IF EXISTS invoices')
            db.session.execute('DROP TABLE IF EXISTS subscription_history')
            db.session.execute('DROP TABLE IF EXISTS subscriptions')
            db.session.execute('DROP TABLE IF EXISTS stripe_customers')
            db.session.execute('DROP TABLE IF EXISTS plans')
            
            db.session.commit()
            print("✅ Subscription tables dropped successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Rollback failed: {str(e)}")
            sys.exit(1)

def check_migration_status():
    """Check if the subscription system migration has been applied"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if subscription tables exist
            result = db.session.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('plans', 'subscriptions', 'stripe_customers', 'invoices', 'subscription_history')")
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📊 Subscription System Status:")
            print(f"   Tables found: {len(tables)}/5")
            
            if len(tables) == 5:
                plan_count = Plan.query.count()
                print(f"   Default plans: {plan_count}")
                print("   Status: ✅ INSTALLED")
                
                if plan_count > 0:
                    print("\n📋 Available Plans:")
                    plans = Plan.query.all()
                    for plan in plans:
                        print(f"   • {plan.name} - ${plan.price}/{plan.interval} ({'Active' if plan.active else 'Inactive'})")
                
            else:
                print("   Status: ❌ NOT INSTALLED")
                print(f"   Missing tables: {set(['plans', 'subscriptions', 'stripe_customers', 'invoices', 'subscription_history']) - set(tables)}")
                
        except Exception as e:
            print(f"❌ Status check failed: {str(e)}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Stripe Subscription System Migration')
    parser.add_argument('action', choices=['migrate', 'rollback', 'status'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'migrate':
        run_migration()
    elif args.action == 'rollback':
        rollback_migration()
    elif args.action == 'status':
        check_migration_status()