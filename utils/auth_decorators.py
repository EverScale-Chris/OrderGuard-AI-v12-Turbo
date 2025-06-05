from functools import wraps
from flask import request, jsonify, session, redirect, url_for, g
from utils.supabase_auth import supabase_auth
from utils.db_adapter import db_adapter, DatabaseMode
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

def login_required(f: Callable) -> Callable:
    """Decorator for routes that require authentication
    
    Works with both Supabase Auth (when in SUPABASE mode) and Flask-Login (fallback).
    Sets g.user with the authenticated user object.
    
    Args:
        f: The route function to protect
        
    Returns:
        Wrapped function that enforces authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if db_adapter.mode == DatabaseMode.SUPABASE:
                # Supabase auth check
                session_data = supabase_auth.get_session_from_request()
                
                if not session_data:
                    logger.warning("No valid session found for protected route")
                    if request.is_json:
                        return jsonify({"error": "Authentication required"}), 401
                    return redirect(url_for('login', next=request.url))
                
                # Store user in g for request context
                g.user = session_data['user']
                g.access_token = session_data['access_token']
                
            else:
                # Fall back to Flask-Login
                try:
                    from flask_login import current_user
                    if not current_user.is_authenticated:
                        logger.warning("Flask-Login user not authenticated")
                        if request.is_json:
                            return jsonify({"error": "Authentication required"}), 401
                        return redirect(url_for('login', next=request.url))
                    g.user = current_user
                    
                except ImportError:
                    logger.error("Flask-Login not available and not in Supabase mode")
                    if request.is_json:
                        return jsonify({"error": "Authentication system unavailable"}), 500
                    return redirect(url_for('login'))
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error in protected route: {e}")
            if request.is_json:
                return jsonify({"error": "Authentication error"}), 500
            return redirect(url_for('login'))
    
    return decorated_function

def organization_required(f: Callable) -> Callable:
    """Decorator for routes that require organization context
    
    Must be used after @login_required. Ensures the user belongs to an organization
    and sets g.organization_id for the request context.
    
    Args:
        f: The route function to protect
        
    Returns:
        Wrapped function that enforces organization membership
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not hasattr(g, 'user') or not g.user:
                logger.warning("organization_required called without authenticated user")
                if request.is_json:
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for('login'))
            
            if db_adapter.mode == DatabaseMode.SUPABASE:
                # Get user's organization from Supabase
                from repositories.user_repository import UserRepository
                user_repo = UserRepository()
                
                # Get user data from repository
                user_data = user_repo.get_by_id(g.user.id)
                
                if not user_data or not user_data.get('organization_id'):
                    logger.warning(f"User {g.user.id} has no organization")
                    if request.is_json:
                        return jsonify({"error": "Organization membership required"}), 403
                    return redirect(url_for('setup_organization'))
                
                g.organization_id = user_data['organization_id']
                g.user_role = user_data.get('role', 'member')
                
            else:
                # Fallback for Flask-Login mode
                if hasattr(g.user, 'organization_id') and g.user.organization_id:
                    g.organization_id = g.user.organization_id
                    g.user_role = getattr(g.user, 'role', 'member')
                else:
                    logger.warning(f"Flask-Login user {g.user.id} has no organization")
                    if request.is_json:
                        return jsonify({"error": "Organization membership required"}), 403
                    return redirect(url_for('setup_organization'))
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Organization check error: {e}")
            if request.is_json:
                return jsonify({"error": "Organization verification error"}), 500
            return redirect(url_for('dashboard'))
    
    return decorated_function

def admin_required(f: Callable) -> Callable:
    """Decorator for routes that require admin role
    
    Must be used after @login_required and @organization_required.
    Ensures the user has admin/owner role in their organization.
    
    Args:
        f: The route function to protect
        
    Returns:
        Wrapped function that enforces admin access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not hasattr(g, 'user_role'):
                logger.warning("admin_required called without user role")
                if request.is_json:
                    return jsonify({"error": "Access denied"}), 403
                return redirect(url_for('dashboard'))
            
            # Check if user has admin privileges
            admin_roles = ['admin', 'owner']
            if g.user_role not in admin_roles:
                logger.warning(f"User {g.user.id} attempted admin action with role: {g.user_role}")
                if request.is_json:
                    return jsonify({"error": "Admin access required"}), 403
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Admin check error: {e}")
            if request.is_json:
                return jsonify({"error": "Access verification error"}), 500
            return redirect(url_for('dashboard'))
    
    return decorated_function

def api_auth_required(f: Callable) -> Callable:
    """Decorator for API routes that require authentication
    
    Similar to @login_required but designed specifically for API endpoints.
    Always returns JSON responses.
    
    Args:
        f: The API route function to protect
        
    Returns:
        Wrapped function that enforces API authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            access_token = None
            
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
            else:
                # Fall back to session token
                access_token = session.get('access_token')
            
            if not access_token:
                return jsonify({"error": "Access token required"}), 401
            
            if db_adapter.mode == DatabaseMode.SUPABASE:
                # Verify token with Supabase
                user = supabase_auth.get_user_from_token(access_token)
                if not user:
                    return jsonify({"error": "Invalid or expired token"}), 401
                
                g.user = user
                g.access_token = access_token
                
            else:
                # For Flask-Login mode, validate session
                from flask_login import current_user
                if not current_user.is_authenticated:
                    return jsonify({"error": "Invalid session"}), 401
                g.user = current_user
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"API authentication error: {e}")
            return jsonify({"error": "Authentication error"}), 500
    
    return decorated_function

def optional_auth(f: Callable) -> Callable:
    """Decorator for routes where authentication is optional
    
    Sets g.user if authenticated, but doesn't require authentication.
    Useful for public pages that show different content for logged-in users.
    
    Args:
        f: The route function
        
    Returns:
        Wrapped function with optional authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            g.user = None
            g.authenticated = False
            
            if db_adapter.mode == DatabaseMode.SUPABASE:
                session_data = supabase_auth.get_session_from_request()
                if session_data:
                    g.user = session_data['user']
                    g.authenticated = True
                    g.access_token = session_data['access_token']
            else:
                try:
                    from flask_login import current_user
                    if current_user.is_authenticated:
                        g.user = current_user
                        g.authenticated = True
                except ImportError:
                    pass
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Optional auth error: {e}")
            # Don't fail the request, just proceed without auth
            g.user = None
            g.authenticated = False
            return f(*args, **kwargs)
    
    return decorated_function

def get_current_user() -> Optional[Any]:
    """Helper function to get the current authenticated user
    
    Returns:
        Current user object if authenticated, None otherwise
    """
    return getattr(g, 'user', None)

def get_current_organization_id() -> Optional[str]:
    """Helper function to get the current user's organization ID
    
    Returns:
        Organization ID if user is authenticated and has organization, None otherwise
    """
    return getattr(g, 'organization_id', None)

def is_admin() -> bool:
    """Helper function to check if current user is admin
    
    Returns:
        True if user has admin/owner role, False otherwise
    """
    user_role = getattr(g, 'user_role', None)
    return user_role in ['admin', 'owner'] if user_role else False 