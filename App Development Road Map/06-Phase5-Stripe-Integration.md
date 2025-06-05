# Phase 5: Stripe Integration for B2B SaaS

## Overview
Implement Stripe payment processing for B2B subscription management, including plan setup, checkout flow, billing portal, and webhook handling.

## Prerequisites
- Phases 1-4 completed
- Stripe account with business verification
- Test mode enabled in Stripe
- Webhook endpoint accessible

## Step-by-Step Implementation

### Step 1: Stripe Configuration

1. **Install Stripe CLI (for testing)**
   ```bash
   # On macOS
   brew install stripe/stripe-cli/stripe
   
   # Login to Stripe
   stripe login
   ```

2. **Create Stripe products and prices**
   ```python
   # scripts/setup_stripe_products.py
   import stripe
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
   
   def create_products():
       """Create subscription products in Stripe"""
       
       # Starter Plan
       starter_product = stripe.Product.create(
           name="OrderGuard Starter",
           description="For small businesses processing up to 50 POs/month"
       )
       
       starter_price = stripe.Price.create(
           product=starter_product.id,
           unit_amount=4900,  # $49.00
           currency="usd",
           recurring={"interval": "month"},
           metadata={"plan": "starter", "po_limit": "50"}
       )
       
       # Professional Plan
       pro_product = stripe.Product.create(
           name="OrderGuard Professional",
           description="For growing businesses processing up to 200 POs/month"
       )
       
       pro_price = stripe.Price.create(
           product=pro_product.id,
           unit_amount=9900,  # $99.00
           currency="usd",
           recurring={"interval": "month"},
           metadata={"plan": "professional", "po_limit": "200"}
       )
       
       # Enterprise Plan
       enterprise_product = stripe.Product.create(
           name="OrderGuard Enterprise",
           description="For large businesses with unlimited PO processing"
       )
       
       enterprise_price = stripe.Price.create(
           product=enterprise_product.id,
           unit_amount=29900,  # $299.00
           currency="usd",
           recurring={"interval": "month"},
           metadata={"plan": "enterprise", "po_limit": "unlimited"}
       )
       
       print("Products created:")
       print(f"Starter: {starter_price.id}")
       print(f"Professional: {pro_price.id}")
       print(f"Enterprise: {enterprise_price.id}")
   
   if __name__ == "__main__":
       create_products()
   ```

### Step 2: Create Subscription Models

1. **Update Supabase schema**
   ```sql
   -- Add to organizations table
   ALTER TABLE organizations
   ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'trialing',
   ADD COLUMN subscription_plan VARCHAR(50) DEFAULT 'starter',
   ADD COLUMN trial_ends_at TIMESTAMP DEFAULT (NOW() + INTERVAL '14 days'),
   ADD COLUMN current_period_end TIMESTAMP;
   
   -- Create subscriptions table for history
   CREATE TABLE subscriptions (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
       stripe_subscription_id VARCHAR(255) UNIQUE,
       stripe_price_id VARCHAR(255),
       status VARCHAR(50),
       current_period_start TIMESTAMP,
       current_period_end TIMESTAMP,
       cancel_at_period_end BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   
   -- Create usage tracking table
   CREATE TABLE usage_tracking (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
       metric_name VARCHAR(100),
       metric_value INTEGER,
       period_start TIMESTAMP,
       period_end TIMESTAMP,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- RLS policies for subscriptions
   ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY "Users can view their organization's subscriptions"
   ON subscriptions FOR SELECT
   TO authenticated
   USING (
       organization_id IN (
           SELECT organization_id FROM users
           WHERE id = auth.uid()
       )
   );
   ```

### Step 3: Create Billing Module

1. **Create billing service**
   ```python
   # utils/billing.py
   import stripe
   import os
   from datetime import datetime, timedelta
   from utils.supabase_client import get_supabase_client
   
   stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
   
   class BillingService:
       def __init__(self):
           self.supabase = get_supabase_client()
           
       def create_checkout_session(self, price_id, organization_id, user_email):
           """Create Stripe checkout session"""
           try:
               # Get organization details
               org = self.supabase.table('organizations').select('*').eq(
                   'id', organization_id
               ).single().execute()
               
               session = stripe.checkout.Session.create(
                   customer_email=user_email,
                   payment_method_types=['card'],
                   line_items=[{
                       'price': price_id,
                       'quantity': 1,
                   }],
                   mode='subscription',
                   success_url=os.environ.get('APP_URL') + '/billing/success?session_id={CHECKOUT_SESSION_ID}',
                   cancel_url=os.environ.get('APP_URL') + '/billing/cancel',
                   metadata={
                       'organization_id': organization_id,
                   },
                   subscription_data={
                       'trial_period_days': 14,
                       'metadata': {
                           'organization_id': organization_id,
                       }
                   }
               )
               
               return session
           except Exception as e:
               print(f"Error creating checkout session: {e}")
               return None
               
       def create_portal_session(self, organization_id):
           """Create customer portal session"""
           try:
               # Get Stripe customer ID
               org = self.supabase.table('organizations').select(
                   'stripe_customer_id'
               ).eq('id', organization_id).single().execute()
               
               if not org.data['stripe_customer_id']:
                   return None
                   
               session = stripe.billing_portal.Session.create(
                   customer=org.data['stripe_customer_id'],
                   return_url=os.environ.get('APP_URL') + '/billing',
               )
               
               return session
           except Exception as e:
               print(f"Error creating portal session: {e}")
               return None
               
       def check_usage_limits(self, organization_id):
           """Check if organization is within plan limits"""
           try:
               # Get organization plan
               org = self.supabase.table('organizations').select(
                   'subscription_plan'
               ).eq('id', organization_id).single().execute()
               
               plan = org.data['subscription_plan']
               
               # Get current month usage
               current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
               
               usage = self.supabase.table('processed_pos').select(
                   'id', count='exact'
               ).eq('organization_id', organization_id).gte(
                   'processed_at', current_month_start.isoformat()
               ).execute()
               
               current_usage = usage.count
               
               # Check limits
               limits = {
                   'starter': 50,
                   'professional': 200,
                   'enterprise': float('inf')
               }
               
               limit = limits.get(plan, 50)
               
               return {
                   'current_usage': current_usage,
                   'limit': limit,
                   'percentage': (current_usage / limit * 100) if limit != float('inf') else 0,
                   'can_process': current_usage < limit
               }
           except Exception as e:
               print(f"Error checking usage: {e}")
               return {'can_process': True, 'current_usage': 0, 'limit': 50}
   ```

### Step 4: Create Billing Routes

1. **Add billing routes to app.py**
   ```python
   # Add to app.py
   from utils.billing import BillingService
   
   billing_service = BillingService()
   
   @app.route('/billing')
   @login_required
   def billing():
       """Billing dashboard"""
       # Get organization details with subscription info
       org = get_user_organization(current_user.id)
       usage = billing_service.check_usage_limits(org['id'])
       
       # Get subscription details
       subscription = None
       if org.get('stripe_subscription_id'):
           try:
               subscription = stripe.Subscription.retrieve(
                   org['stripe_subscription_id']
               )
           except:
               pass
       
       return render_template('billing.html', 
                            organization=org,
                            usage=usage,
                            subscription=subscription)
   
   @app.route('/billing/checkout', methods=['POST'])
   @login_required
   def create_checkout():
       """Create checkout session"""
       price_id = request.form.get('price_id')
       org = get_user_organization(current_user.id)
       
       session = billing_service.create_checkout_session(
           price_id=price_id,
           organization_id=org['id'],
           user_email=current_user.email
       )
       
       if session:
           return redirect(session.url, code=303)
       else:
           flash('Error creating checkout session', 'error')
           return redirect(url_for('billing'))
   
   @app.route('/billing/portal', methods=['POST'])
   @login_required
   def create_portal():
       """Create customer portal session"""
       org = get_user_organization(current_user.id)
       
       session = billing_service.create_portal_session(org['id'])
       
       if session:
           return redirect(session.url, code=303)
       else:
           flash('Error accessing billing portal', 'error')
           return redirect(url_for('billing'))
   ```

### Step 5: Webhook Handler

1. **Create webhook endpoint**
   ```python
   # Add to app.py
   @app.route('/stripe/webhook', methods=['POST'])
   def stripe_webhook():
       """Handle Stripe webhooks"""
       payload = request.get_data()
       sig_header = request.headers.get('Stripe-Signature')
       endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
       
       try:
           event = stripe.Webhook.construct_event(
               payload, sig_header, endpoint_secret
           )
       except ValueError:
           return jsonify({'error': 'Invalid payload'}), 400
       except stripe.error.SignatureVerificationError:
           return jsonify({'error': 'Invalid signature'}), 400
       
       # Handle the event
       if event['type'] == 'checkout.session.completed':
           session = event['data']['object']
           handle_checkout_session_completed(session)
           
       elif event['type'] == 'customer.subscription.updated':
           subscription = event['data']['object']
           handle_subscription_updated(subscription)
           
       elif event['type'] == 'customer.subscription.deleted':
           subscription = event['data']['object']
           handle_subscription_deleted(subscription)
           
       elif event['type'] == 'invoice.payment_failed':
           invoice = event['data']['object']
           handle_payment_failed(invoice)
       
       return jsonify({'received': True})
   
   def handle_checkout_session_completed(session):
       """Handle successful checkout"""
       org_id = session['metadata']['organization_id']
       
       # Update organization with Stripe IDs
       supabase = get_supabase_client()
       supabase.table('organizations').update({
           'stripe_customer_id': session['customer'],
           'stripe_subscription_id': session['subscription'],
           'subscription_status': 'active'
       }).eq('id', org_id).execute()
       
       # Create subscription record
       supabase.table('subscriptions').insert({
           'organization_id': org_id,
           'stripe_subscription_id': session['subscription'],
           'status': 'active'
       }).execute()
   ```

### Step 6: Usage Enforcement

1. **Add usage checks to PO processing**
   ```python
   # Modify process_purchase_order in app.py
   @app.route('/api/process-po', methods=['POST'])
   @login_required
   def process_purchase_order():
       # Check usage limits first
       org = get_user_organization(current_user.id)
       usage = billing_service.check_usage_limits(org['id'])
       
       if not usage['can_process']:
           return jsonify({
               "error": f"Monthly limit reached ({usage['limit']} POs). Please upgrade your plan.",
               "usage": usage
           }), 403
       
       # ... rest of existing code ...
   ```

### Step 7: Create Billing UI

1. **Create billing template**
   ```html
   <!-- templates/billing.html -->
   {% extends "base.html" %}
   {% block content %}
   <div class="container mx-auto px-4 py-8">
       <h1 class="text-3xl font-bold mb-8">Billing & Subscription</h1>
       
       <!-- Current Plan -->
       <div class="bg-white rounded-lg shadow p-6 mb-6">
           <h2 class="text-xl font-semibold mb-4">Current Plan</h2>
           <p class="text-lg">{{ organization.subscription_plan|title }}</p>
           <p class="text-gray-600">Status: {{ organization.subscription_status|title }}</p>
           
           {% if organization.trial_ends_at and organization.subscription_status == 'trialing' %}
           <p class="text-sm text-orange-600 mt-2">
               Trial ends: {{ organization.trial_ends_at.strftime('%B %d, %Y') }}
           </p>
           {% endif %}
       </div>
       
       <!-- Usage -->
       <div class="bg-white rounded-lg shadow p-6 mb-6">
           <h2 class="text-xl font-semibold mb-4">Usage This Month</h2>
           <div class="mb-4">
               <div class="flex justify-between mb-2">
                   <span>POs Processed</span>
                   <span>{{ usage.current_usage }} / {{ usage.limit if usage.limit != inf else 'Unlimited' }}</span>
               </div>
               <div class="w-full bg-gray-200 rounded-full h-2">
                   <div class="bg-blue-600 h-2 rounded-full" style="width: {{ usage.percentage }}%"></div>
               </div>
           </div>
       </div>
       
       <!-- Pricing Plans -->
       <div class="grid md:grid-cols-3 gap-6 mb-8">
           <!-- Starter Plan -->
           <div class="bg-white rounded-lg shadow p-6">
               <h3 class="text-xl font-semibold mb-2">Starter</h3>
               <p class="text-3xl font-bold mb-4">$49<span class="text-sm font-normal">/month</span></p>
               <ul class="mb-6">
                   <li>✓ 50 POs per month</li>
                   <li>✓ 5 price books</li>
                   <li>✓ Email support</li>
               </ul>
               {% if organization.subscription_plan != 'starter' %}
               <form action="{{ url_for('create_checkout') }}" method="POST">
                   <input type="hidden" name="price_id" value="{{ starter_price_id }}">
                   <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                       Select Plan
                   </button>
               </form>
               {% else %}
               <button class="w-full bg-gray-300 text-gray-600 py-2 rounded" disabled>
                   Current Plan
               </button>
               {% endif %}
           </div>
           
           <!-- Professional Plan -->
           <div class="bg-white rounded-lg shadow p-6 border-2 border-blue-600">
               <div class="bg-blue-600 text-white text-sm px-2 py-1 rounded inline-block mb-2">
                   Most Popular
               </div>
               <h3 class="text-xl font-semibold mb-2">Professional</h3>
               <p class="text-3xl font-bold mb-4">$99<span class="text-sm font-normal">/month</span></p>
               <ul class="mb-6">
                   <li>✓ 200 POs per month</li>
                   <li>✓ Unlimited price books</li>
                   <li>✓ Priority support</li>
                   <li>✓ Advanced analytics</li>
               </ul>
               {% if organization.subscription_plan != 'professional' %}
               <form action="{{ url_for('create_checkout') }}" method="POST">
                   <input type="hidden" name="price_id" value="{{ pro_price_id }}">
                   <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                       Select Plan
                   </button>
               </form>
               {% else %}
               <button class="w-full bg-gray-300 text-gray-600 py-2 rounded" disabled>
                   Current Plan
               </button>
               {% endif %}
           </div>
           
           <!-- Enterprise Plan -->
           <div class="bg-white rounded-lg shadow p-6">
               <h3 class="text-xl font-semibold mb-2">Enterprise</h3>
               <p class="text-3xl font-bold mb-4">$299<span class="text-sm font-normal">/month</span></p>
               <ul class="mb-6">
                   <li>✓ Unlimited POs</li>
                   <li>✓ Unlimited price books</li>
                   <li>✓ Dedicated support</li>
                   <li>✓ Custom integrations</li>
                   <li>✓ SLA guarantee</li>
               </ul>
               {% if organization.subscription_plan != 'enterprise' %}
               <form action="{{ url_for('create_checkout') }}" method="POST">
                   <input type="hidden" name="price_id" value="{{ enterprise_price_id }}">
                   <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                       Select Plan
                   </button>
               </form>
               {% else %}
               <button class="w-full bg-gray-300 text-gray-600 py-2 rounded" disabled>
                   Current Plan
               </button>
               {% endif %}
           </div>
       </div>
       
       <!-- Manage Subscription -->
       {% if organization.stripe_customer_id %}
       <div class="bg-white rounded-lg shadow p-6">
           <h2 class="text-xl font-semibold mb-4">Manage Subscription</h2>
           <form action="{{ url_for('create_portal') }}" method="POST">
               <button class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
                   Open Customer Portal
               </button>
           </form>
           <p class="text-sm text-gray-600 mt-2">
               Update payment method, download invoices, or cancel subscription
           </p>
       </div>
       {% endif %}
   </div>
   {% endblock %}
   ```

### Step 8: Testing

1. **Set up Stripe CLI for webhook testing**
   ```bash
   # Forward webhooks to local app
   stripe listen --forward-to localhost:5000/stripe/webhook
   
   # Note the webhook signing secret and add to .env
   ```

2. **Test checkout flow**
   ```bash
   # Use test cards
   # Success: 4242 4242 4242 4242
   # Decline: 4000 0000 0000 0002
   ```

## Verification Checklist

- [ ] Stripe products and prices created
- [ ] Database schema updated with subscription fields
- [ ] Billing service implemented
- [ ] Checkout flow working
- [ ] Customer portal accessible
- [ ] Webhooks handling events
- [ ] Usage limits enforced
- [ ] Billing UI complete
- [ ] Test payments successful

## Common Issues & Solutions

1. **Webhook signature verification fails**
   - Ensure you're using the correct webhook secret
   - Check that you're passing the raw request body

2. **Checkout session not updating database**
   - Verify webhook endpoint is accessible
   - Check Stripe webhook logs for errors

3. **Usage limits not enforcing**
   - Ensure organization_id is properly set
   - Check that usage tracking is recording

## Security Considerations

1. **Never expose secret keys**
   - Use environment variables
   - Different keys for test/production

2. **Validate webhook signatures**
   - Always verify Stripe webhook signatures
   - Return early on validation failure

3. **Secure checkout flow**
   - Use Stripe-hosted checkout
   - Don't store card details

## Next Steps
Proceed to Phase 6: Feature Enhancement and Admin Dashboard 