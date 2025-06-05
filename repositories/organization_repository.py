"""
Organization Repository for Supabase operations
Handles organization management and subscription tracking
"""

from typing import List, Optional
from uuid import UUID
from repositories.base import BaseRepository
from models.supabase_models import Organization

class OrganizationRepository(BaseRepository[Organization]):
    """Repository for organization operations"""
    
    def __init__(self):
        super().__init__('organizations', Organization)
    
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        results = self.get_all({'slug': slug})
        return results[0] if results else None
    
    def get_by_stripe_customer_id(self, customer_id: str) -> Optional[Organization]:
        """Get organization by Stripe customer ID"""
        results = self.get_all({'stripe_customer_id': customer_id})
        return results[0] if results else None
    
    def get_active_organizations(self) -> List[Organization]:
        """Get all active organizations"""
        return self.get_all({'is_active': True})
    
    def get_trial_organizations(self) -> List[Organization]:
        """Get organizations in trial status"""
        return self.get_all({'subscription_status': 'trial'})
    
    def increment_po_count(self, org_id: UUID) -> bool:
        """Increment monthly PO count for organization"""
        try:
            # This is handled by database trigger, but we can also do it manually
            response = self.client.rpc('increment_organization_po_count', {
                'org_id': str(org_id)
            }).execute()
            return True
        except Exception as e:
            print(f"Error incrementing PO count: {e}")
            return False
    
    def reset_monthly_count(self, org_id: UUID) -> bool:
        """Reset monthly PO count for organization"""
        try:
            from datetime import datetime, timedelta
            next_month = datetime.now() + timedelta(days=30)
            
            data = {
                'monthly_po_count': 0,
                'reset_date': next_month.date().isoformat()
            }
            
            updated = self.update(org_id, data)
            return updated is not None
        except Exception as e:
            print(f"Error resetting monthly count: {e}")
            return False
    
    def check_po_limit(self, org_id: UUID) -> dict:
        """Check if organization can process more POs"""
        try:
            org = self.get_by_id(org_id)
            if not org:
                return {'can_process': False, 'reason': 'Organization not found'}
            
            if not org.is_active:
                return {'can_process': False, 'reason': 'Organization is inactive'}
            
            # Enterprise has unlimited
            if org.subscription_plan == 'enterprise':
                return {'can_process': True, 'remaining': 'unlimited'}
            
            # Check monthly limit
            remaining = org.monthly_po_limit - org.monthly_po_count
            can_process = remaining > 0
            
            return {
                'can_process': can_process,
                'remaining': remaining,
                'limit': org.monthly_po_limit,
                'used': org.monthly_po_count,
                'plan': org.subscription_plan
            }
        except Exception as e:
            print(f"Error checking PO limit: {e}")
            return {'can_process': False, 'reason': f'Error: {e}'}
    
    def update_subscription(self, org_id: UUID, plan: str, status: str, 
                          stripe_subscription_id: str = None) -> Optional[Organization]:
        """Update organization subscription details"""
        try:
            # Set limits based on plan
            limits = {
                'starter': 50,
                'professional': 200,
                'enterprise': 999999  # Effectively unlimited
            }
            
            data = {
                'subscription_plan': plan,
                'subscription_status': status,
                'monthly_po_limit': limits.get(plan, 50)
            }
            
            if stripe_subscription_id:
                data['stripe_subscription_id'] = stripe_subscription_id
            
            return self.update(org_id, data)
        except Exception as e:
            print(f"Error updating subscription: {e}")
            return None
    
    def get_organizations_by_plan(self, plan: str) -> List[Organization]:
        """Get organizations by subscription plan"""
        return self.get_all({'subscription_plan': plan})
    
    def search_organizations(self, search_term: str) -> List[Organization]:
        """Search organizations by name or slug"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .or_(f'name.ilike.%{search_term}%,slug.ilike.%{search_term}%')\
                .execute()
            
            if response.data:
                return [self.model_class.from_dict(item) for item in response.data]
            return []
        except Exception as e:
            print(f"Error searching organizations: {e}")
            return [] 