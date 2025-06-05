from functools import wraps
from flask import request, jsonify, session, redirect, url_for, g
from utils.supabase_client import get_supabase_client
import jwt
import os
from typing import Dict, Optional, Any

class SupabaseAuth:
    """Wrapper for Supabase Authentication operations"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
    
    def sign_up(self, email: str, password: str, username: str, **metadata) -> Dict[str, Any]:
        """Register new user with Supabase Auth
        
        Args:
            email: User's email address
            password: User's password
            username: Display username
            **metadata: Additional user metadata
            
        Returns:
            Dictionary with success status, user data, and session info
        """
        try:
            # Prepare user metadata
            user_metadata = {
                "username": username,
                **metadata
            }
            
            # Create auth user
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata
                }
            })
            
            if auth_response.user:
                return {
                    "success": True,
                    "user": auth_response.user,
                    "session": auth_response.session,
                    "message": "User created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create user"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in user with email and password
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dictionary with success status, user data, and session info
        """
        try:
            auth_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.session:
                return {
                    "success": True,
                    "session": auth_response.session,
                    "user": auth_response.user,
                    "message": "Login successful"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self, access_token: Optional[str] = None) -> Dict[str, Any]:
        """Sign out user
        
        Args:
            access_token: Optional access token to sign out specific session
            
        Returns:
            Dictionary with success status
        """
        try:
            if access_token:
                self.client.auth.set_session(access_token)
            
            self.client.auth.sign_out()
            return {"success": True, "message": "Logout successful"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_from_token(self, access_token: str) -> Optional[Any]:
        """Get user information from JWT access token
        
        Args:
            access_token: JWT access token
            
        Returns:
            User object if valid, None if invalid
        """
        try:
            # Set the session with the access token
            response = self.client.auth.set_session(access_token)
            if response.user:
                return response.user
            return None
            
        except Exception as e:
            print(f"Error getting user from token: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            Dictionary with success status and new session info
        """
        try:
            response = self.client.auth.refresh_session(refresh_token)
            
            if response.session:
                return {
                    "success": True,
                    "session": response.session,
                    "message": "Token refreshed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to refresh token"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_password_reset(self, email: str) -> Dict[str, Any]:
        """Send password reset email
        
        Args:
            email: User's email address
            
        Returns:
            Dictionary with success status
        """
        try:
            response = self.client.auth.reset_password_email(email)
            return {
                "success": True,
                "message": "Password reset email sent"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_user(self, access_token: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information
        
        Args:
            access_token: User's access token
            updates: Dictionary of fields to update
            
        Returns:
            Dictionary with success status and updated user
        """
        try:
            # Set session
            self.client.auth.set_session(access_token)
            
            # Update user
            response = self.client.auth.update_user(updates)
            
            if response.user:
                return {
                    "success": True,
                    "user": response.user,
                    "message": "User updated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update user"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_session_from_request(self) -> Optional[Dict[str, Any]]:
        """Extract session information from current Flask request
        
        Returns:
            Session dictionary if valid, None if invalid
        """
        access_token = session.get('access_token')
        refresh_token = session.get('refresh_token')
        
        if not access_token:
            return None
        
        # Verify token is still valid
        user = self.get_user_from_token(access_token)
        if not user:
            # Try to refresh token
            if refresh_token:
                refresh_result = self.refresh_token(refresh_token)
                if refresh_result['success']:
                    # Update session with new tokens
                    session['access_token'] = refresh_result['session'].access_token
                    session['refresh_token'] = refresh_result['session'].refresh_token
                    return {
                        'access_token': refresh_result['session'].access_token,
                        'refresh_token': refresh_result['session'].refresh_token,
                        'user': self.get_user_from_token(refresh_result['session'].access_token)
                    }
            return None
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user
        }

# Global instance
supabase_auth = SupabaseAuth() 