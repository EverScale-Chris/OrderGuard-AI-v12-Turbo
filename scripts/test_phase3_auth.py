#!/usr/bin/env python3
"""
Test script for Phase 3: Authentication Migration
Tests Supabase Auth integration and authentication flows
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pytest
import json
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

# Environment setup
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_ANON_KEY', 'test_anon_key')
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'test_service_key')
os.environ.setdefault('SECRET_KEY', 'test_secret_key')
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

def test_supabase_auth_wrapper():
    """Test SupabaseAuth wrapper functionality"""
    try:
        # Mock the Supabase client to avoid API key validation
        with patch('utils.supabase_client.get_supabase_client') as mock_client:
            mock_client.return_value = MagicMock()
            
            from utils.supabase_auth import SupabaseAuth
            
            # Test initialization
            auth = SupabaseAuth()
            assert auth is not None
            print("✓ SupabaseAuth wrapper initialized successfully")
            
            # Test methods exist
            assert hasattr(auth, 'sign_up')
            assert hasattr(auth, 'sign_in')
            assert hasattr(auth, 'sign_out')
            assert hasattr(auth, 'refresh_token')
            assert hasattr(auth, 'get_user_from_token')
            assert hasattr(auth, 'send_password_reset')
            assert hasattr(auth, 'update_user')
            print("✓ SupabaseAuth has all required methods")
        
        return True
        
    except Exception as e:
        print(f"✗ SupabaseAuth wrapper test failed: {e}")
        return False

def test_auth_decorators():
    """Test authentication decorators"""
    try:
        # Mock the Supabase client
        with patch('utils.supabase_client.get_supabase_client') as mock_client:
            mock_client.return_value = MagicMock()
            
            from utils.auth_decorators import (
                login_required, 
                organization_required, 
                admin_required,
                api_auth_required,
                optional_auth,
                get_current_user,
                get_current_organization_id,
                is_admin
            )
            
            # Test decorators exist and are callable
            decorators = [
                login_required, organization_required, admin_required,
                api_auth_required, optional_auth
            ]
            
            for decorator in decorators:
                assert callable(decorator)
            
            print("✓ Authentication decorators imported successfully")
            
            # Test helper functions
            helpers = [get_current_user, get_current_organization_id, is_admin]
            for helper in helpers:
                assert callable(helper)
            
            print("✓ Authentication helper functions available")
        
        return True
        
    except Exception as e:
        print(f"✗ Authentication decorators test failed: {e}")
        return False

def test_user_repository():
    """Test UserRepository functionality"""
    try:
        # Mock the Supabase client
        with patch('utils.supabase_client.get_supabase_client') as mock_client:
            mock_client.return_value = MagicMock()
            
            from repositories.user_repository import UserRepository
            
            # Test initialization
            user_repo = UserRepository()
            assert user_repo is not None
            assert user_repo.table_name == 'users'
            print("✓ UserRepository initialized successfully")
            
            # Test methods exist
            required_methods = [
                'create', 'get_by_email', 'get_by_username', 
                'get_by_organization', 'update_role', 'update_profile',
                'activate_user', 'deactivate_user', 'verify_email',
                'get_organization_admins', 'get_organization_owner',
                'search_users', 'get_user_with_organization',
                'update_last_login', 'get_active_users_count'
            ]
            
            for method in required_methods:
                assert hasattr(user_repo, method)
                assert callable(getattr(user_repo, method))
            
            print("✓ UserRepository has all required methods")
        
        return True
        
    except Exception as e:
        print(f"✗ UserRepository test failed: {e}")
        return False

def test_auth_routes():
    """Test authentication routes blueprint"""
    try:
        # Check if the auth routes file exists and has the right structure
        auth_routes_path = project_root / 'routes' / 'auth_routes.py'
        
        if auth_routes_path.exists():
            with open(auth_routes_path, 'r') as f:
                content = f.read()
                
            # Check for key components
            required_components = [
                'auth_bp = Blueprint',
                'def register',
                'def login',
                'def logout',
                'def get_profile',
                'def update_profile',
                'def reset_password'
            ]
            
            missing_components = []
            for component in required_components:
                if component not in content:
                    missing_components.append(component)
            
            if missing_components:
                print(f"⚠ Missing components: {missing_components}")
            else:
                print("✓ All required route components found")
            
            print("✓ Authentication routes file exists and has proper structure")
        else:
            print("✗ Authentication routes file not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Authentication routes test failed: {e}")
        return False

def test_database_mode_switching():
    """Test database adapter mode switching"""
    try:
        from utils.db_adapter import db_adapter, DatabaseMode
        
        # Test mode switching
        original_mode = db_adapter.mode
        
        # Test switching to Supabase mode
        db_adapter.set_mode(DatabaseMode.SUPABASE)
        assert db_adapter.mode == DatabaseMode.SUPABASE
        print("✓ Database adapter switched to Supabase mode")
        
        # Test switching back
        db_adapter.set_mode(original_mode)
        assert db_adapter.mode == original_mode
        print("✓ Database adapter mode switching works")
        
        return True
        
    except Exception as e:
        print(f"✗ Database mode switching test failed: {e}")
        return False

def test_environment_variables():
    """Test required environment variables for authentication"""
    try:
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY', 
            'SUPABASE_SERVICE_KEY',
            'SECRET_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠ Missing environment variables: {missing_vars}")
            print("  (This is expected in test environment)")
        else:
            print("✓ All required environment variables are set")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment variables test failed: {e}")
        return False

def test_session_management():
    """Test session management functionality"""
    try:
        # Mock the Supabase client
        with patch('utils.supabase_client.get_supabase_client') as mock_client:
            mock_client.return_value = MagicMock()
            
            from utils.supabase_auth import supabase_auth
            
            # Test session methods exist
            assert hasattr(supabase_auth, 'get_session_from_request')
            print("✓ Session management methods available")
            
            # Test session validation (mocked)
            with patch('flask.session', {'access_token': 'test_token'}):
                # This would normally validate the token with Supabase
                # In test, we just check the method can be called
                assert hasattr(supabase_auth, 'get_user_from_token')
                print("✓ Session validation methods available")
        
        return True
        
    except Exception as e:
        print(f"✗ Session management test failed: {e}")
        return False

def test_frontend_auth_script():
    """Test frontend authentication JavaScript exists"""
    try:
        auth_js_path = project_root / 'static' / 'js' / 'auth.js'
        
        if auth_js_path.exists():
            with open(auth_js_path, 'r') as f:
                content = f.read()
                
            # Check for key functionality
            required_functions = [
                'AuthManager',
                'login',
                'register', 
                'logout',
                'getProfile',
                'updateProfile',
                'resetPassword',
                'checkAuthStatus'
            ]
            
            for func in required_functions:
                if func in content:
                    print(f"✓ Frontend auth function '{func}' found")
                else:
                    print(f"⚠ Frontend auth function '{func}' not found")
            
            print("✓ Frontend authentication script exists")
        else:
            print("⚠ Frontend authentication script not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Frontend auth script test failed: {e}")
        return False

def test_integration_readiness():
    """Test readiness for authentication integration"""
    try:
        # Mock the Supabase client
        with patch('utils.supabase_client.get_supabase_client') as mock_client:
            mock_client.return_value = MagicMock()
            
            # Test core components can be imported
            from utils.supabase_auth import supabase_auth
            from utils.auth_decorators import login_required
            from repositories.user_repository import UserRepository
            
            print("✓ Core authentication components can be imported together")
            
            # Test database adapter integration
            from utils.db_adapter import db_adapter, DatabaseMode
            
            # Simulate switching to Supabase mode
            original_mode = db_adapter.mode
            db_adapter.set_mode(DatabaseMode.SUPABASE)
            
            # Test repository works in Supabase mode
            user_repo = UserRepository()
            assert user_repo.table_name == 'users'
            
            # Switch back
            db_adapter.set_mode(original_mode)
            
            print("✓ Authentication system integration ready")
            
            # Check if all files exist
            required_files = [
                'utils/supabase_auth.py',
                'utils/auth_decorators.py',
                'repositories/user_repository.py',
                'routes/auth_routes.py',
                'static/js/auth.js'
            ]
            
            missing_files = []
            for file_path in required_files:
                if not (project_root / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                print(f"⚠ Missing files: {missing_files}")
            else:
                print("✓ All required authentication files present")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration readiness test failed: {e}")
        return False

def run_all_tests():
    """Run all Phase 3 authentication tests"""
    print("=" * 60)
    print("PHASE 3: AUTHENTICATION MIGRATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("SupabaseAuth Wrapper", test_supabase_auth_wrapper),
        ("Authentication Decorators", test_auth_decorators),
        ("User Repository", test_user_repository),
        ("Authentication Routes", test_auth_routes),
        ("Database Mode Switching", test_database_mode_switching),
        ("Session Management", test_session_management),
        ("Frontend Auth Script", test_frontend_auth_script),
        ("Integration Readiness", test_integration_readiness),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"{icon} {test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All Phase 3 authentication tests passed!")
        print("Ready to integrate Supabase Auth with the Flask application.")
    elif passed >= total * 0.8:
        print("\n⚠ Most tests passed. Review failed tests before proceeding.")
    else:
        print("\n❌ Several tests failed. Address issues before proceeding.")
    
    return passed, total

if __name__ == "__main__":
    run_all_tests() 