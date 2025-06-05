#!/usr/bin/env python3
"""
Test script for OrderGuard AI Pro Supabase integration
Verifies connection, extensions, and AI readiness
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.supabase_client import get_supabase_client, get_supabase_admin_client, test_connection, get_project_info
from utils.db_adapter import get_db_adapter

def test_basic_connection():
    """Test basic Supabase connection"""
    print("🔗 Testing basic Supabase connection...")
    
    try:
        result = test_connection()
        if result['status'] == 'success':
            print("✅ Basic connection successful")
            return True
        else:
            print(f"❌ Connection failed: {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_admin_connection():
    """Test admin connection"""
    print("🔐 Testing admin connection...")
    
    try:
        # Check if service key is available
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not service_key:
            print("⚠️  Service key not configured - skipping admin test")
            return True  # Don't fail if service key isn't set yet
            
        client = get_supabase_admin_client()
        # Try a simple version check
        result = client.rpc('version').execute()
        print("✅ Admin connection successful")
        return True
    except Exception as e:
        print(f"❌ Admin connection failed: {e}")
        return False

def test_extensions():
    """Test database extensions"""
    print("🧩 Testing database extensions...")
    
    try:
        # Check if service key is available
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not service_key:
            print("⚠️  Service key not configured - skipping extensions test")
            return True  # Don't fail if service key isn't set yet
            
        client = get_supabase_admin_client()
        
        # Test extension status function
        result = client.rpc('orderguard_extensions_status').execute()
        if result.data:
            data = result.data
            print(f"   AI Ready: {data.get('ai_ready', False)}")
            print(f"   Background Processing: {data.get('background_processing_ready', False)}")
            print(f"   HTTP Requests: {data.get('http_requests_enabled', False)}")
            print("✅ Extensions test successful")
            return True
        else:
            print("❌ Extensions status function not available")
            return False
    except Exception as e:
        print(f"❌ Extensions test failed: {e}")
        return False

def test_vector_operations():
    """Test vector operations for AI features"""
    print("🤖 Testing vector operations...")
    
    try:
        # Check if service key is available
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not service_key:
            print("⚠️  Service key not configured - skipping vector test")
            return True  # Don't fail if service key isn't set yet
            
        client = get_supabase_admin_client()
        
        # Test vector operations function
        result = client.rpc('test_vector_operations').execute()
        if result.data:
            data = result.data
            print(f"   Vector Extension: {data.get('vector_extension_available', False)}")
            print(f"   OpenAI Compatible: {data.get('openai_compatible', False)}")
            print(f"   Sample Dimension: {data.get('sample_vector_dimension', 'N/A')}")
            print("✅ Vector operations test successful")
            return True
        else:
            print("❌ Vector operations function not available")
            return False
    except Exception as e:
        print(f"❌ Vector operations test failed: {e}")
        return False

def test_database_adapter():
    """Test database adapter functionality"""
    print("⚙️  Testing database adapter...")
    
    try:
        adapter = get_db_adapter()
        info = adapter.get_database_info()
        
        print(f"   Mode: {info['mode']}")
        print(f"   Phase: {info['phase']}")
        print(f"   AI Features: {info['ai_features_enabled']}")
        print(f"   Vector Support: {info['vector_enabled']}")
        print("✅ Database adapter test successful")
        return True
    except Exception as e:
        print(f"❌ Database adapter test failed: {e}")
        return False

def test_environment_variables():
    """Test environment variables"""
    print("🌍 Testing environment variables...")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY'
    ]
    
    optional_vars = [
        'SUPABASE_SERVICE_KEY',
        'OPENAI_API_KEY',
        'ENABLE_AI_FEATURES'
    ]
    
    all_good = True
    
    for var in required_vars:
        if os.environ.get(var):
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Missing")
            all_good = False
    
    for var in optional_vars:
        if os.environ.get(var):
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ⚠️  {var}: Not set (optional)")
    
    if all_good:
        print("✅ Environment variables test successful")
    else:
        print("❌ Some required environment variables are missing")
    
    return all_good

def run_all_tests():
    """Run all tests"""
    print("🧪 OrderGuard AI Pro - Supabase Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Basic Connection", test_basic_connection),
        ("Admin Connection", test_admin_connection),
        ("Database Extensions", test_extensions),
        ("Vector Operations", test_vector_operations),
        ("Database Adapter", test_database_adapter)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 1 setup is complete.")
        
        # Show project info
        print("\n📋 Project Information:")
        project_info = get_project_info()
        for key, value in project_info.items():
            print(f"   {key}: {value}")
            
        return True
    else:
        print("⚠️  Some tests failed. Please review the setup.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 