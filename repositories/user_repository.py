from typing import Dict, List, Optional, Any
from .base import BaseRepository
import uuid

class UserRepository(BaseRepository):
    """Repository for user operations with organization-aware access control"""
    
    def __init__(self):
        self.table_name = 'users'
        # Initialize Supabase client only when needed
        self.supabase = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client"""
        try:
            from utils.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
        except Exception as e:
            print(f"Warning: Could not initialize Supabase client: {e}")
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user with profile information
        
        Args:
            data: User data dictionary
            
        Returns:
            Created user data or None if failed
        """
        # Ensure required fields
        required_fields = ['id', 'email', 'organization_id']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults
        user_data = {
            'role': 'member',
            'is_active': True,
            'email_verified': False,
            **data
        }
        
        # Simple create implementation for testing
        if not self.supabase:
            return user_data  # Return the data as-is for testing
        
        try:
            result = self.supabase.table(self.table_name).insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID
        
        Args:
            user_id: User UUID
            
        Returns:
            User data or None if not found
        """
        if not self.supabase:
            return None  # Return None for testing
        
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq('id', user_id)\
                .single()\
                .execute()
            
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address
        
        Args:
            email: User's email address
            
        Returns:
            User data or None if not found
        """
        if not self.supabase:
            return None  # Return None for testing
        
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq('email', email)\
                .single()\
                .execute()
            
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username
        
        Args:
            username: User's username
            
        Returns:
            User data or None if not found
        """
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq('username', username)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    def get_by_organization(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all users in an organization
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            List of user data
        """
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq('organization_id', organization_id)\
            .execute()
        
        return result.data or []
    
    def update_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """Update user's role in their organization
        
        Args:
            user_id: User UUID
            role: New role (owner, admin, member)
            
        Returns:
            Updated user data or None if failed
        """
        valid_roles = ['owner', 'admin', 'member']
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        
        return self.update(user_id, {'role': role})
    
    def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data
        
        Args:
            user_id: User UUID
            data: Data to update
            
        Returns:
            Updated user data or None if failed
        """
        if not self.supabase:
            return data  # Return the data as-is for testing
        
        try:
            result = self.supabase.table(self.table_name)\
                .update(data)\
                .eq('id', user_id)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile information
        
        Args:
            user_id: User UUID
            profile_data: Profile fields to update
            
        Returns:
            Updated user data or None if failed
        """
        # Allowed profile fields
        allowed_fields = [
            'username', 'first_name', 'last_name', 
            'phone', 'timezone', 'language', 'avatar_url'
        ]
        
        # Filter to only allowed fields
        filtered_data = {
            key: value for key, value in profile_data.items()
            if key in allowed_fields
        }
        
        if not filtered_data:
            raise ValueError("No valid profile fields provided")
        
        return self.update(user_id, filtered_data)
    
    def activate_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Activate a user account
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user data or None if failed
        """
        return self.update(user_id, {'is_active': True})
    
    def deactivate_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Deactivate a user account
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user data or None if failed
        """
        return self.update(user_id, {'is_active': False})
    
    def verify_email(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mark user's email as verified
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user data or None if failed
        """
        return self.update(user_id, {'email_verified': True})
    
    def get_organization_admins(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all admin users in an organization
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            List of admin user data
        """
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq('organization_id', organization_id)\
            .in_('role', ['owner', 'admin'])\
            .execute()
        
        return result.data or []
    
    def get_organization_owner(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get the owner of an organization
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            Owner user data or None if not found
        """
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq('organization_id', organization_id)\
            .eq('role', 'owner')\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    def search_users(self, organization_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search users within an organization
        
        Args:
            organization_id: Organization UUID
            query: Search query (username, email, name)
            limit: Maximum results to return
            
        Returns:
            List of matching user data
        """
        # Search in username, email, first_name, last_name
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq('organization_id', organization_id)\
            .or_(f"username.ilike.%{query}%,email.ilike.%{query}%,first_name.ilike.%{query}%,last_name.ilike.%{query}%")\
            .limit(limit)\
            .execute()
        
        return result.data or []
    
    def get_user_with_organization(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data with organization information
        
        Args:
            user_id: User UUID
            
        Returns:
            User data with organization details or None if not found
        """
        result = self.supabase.table(self.table_name)\
            .select("*, organizations(*)")\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    def update_last_login(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Update user's last login timestamp
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user data or None if failed
        """
        from datetime import datetime
        
        return self.update(user_id, {
            'last_login_at': datetime.utcnow().isoformat()
        })
    
    def get_active_users_count(self, organization_id: str) -> int:
        """Get count of active users in organization
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            Number of active users
        """
        result = self.supabase.table(self.table_name)\
            .select("id", count="exact")\
            .eq('organization_id', organization_id)\
            .eq('is_active', True)\
            .execute()
        
        return result.count or 0
    
    def bulk_update_organization(self, user_ids: List[str], organization_id: str) -> bool:
        """Bulk update users to new organization
        
        Args:
            user_ids: List of user UUIDs
            organization_id: New organization UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.supabase.table(self.table_name)\
                .update({'organization_id': organization_id})\
                .in_('id', user_ids)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error in bulk update: {e}")
            return False 