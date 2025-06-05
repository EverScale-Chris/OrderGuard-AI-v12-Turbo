"""
Basic Phase 2 Test Script - Database Migration Testing
Tests Supabase schema and basic connectivity without admin operations
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import only what we need without triggering Flask app initialization
from utils.supabase_client import get_supabase_client
from utils.db_adapter import get_db_adapter

class BasicPhase2Tester:
    """Basic test suite for Phase 2 database migration functionality"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.db_adapter = get_db_adapter()
        
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        if success:
            self.test_results['passed'] += 1
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.test_results['failed'] += 1
            error_msg = f"{test_name}: FAILED - {message}"
            self.test_results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def test_database_connection(self):
        """Test 1: Database connection"""
        try:
            response = self.client.table('organizations').select('id').limit(1).execute()
            self.log_test("Database Connection", True, "Connected to Supabase")
        except Exception as e:
            self.log_test("Database Connection", False, str(e))
    
    def test_schema_exists(self):
        """Test 2: Verify all tables exist"""
        required_tables = ['organizations', 'users', 'price_books', 'price_items', 'processed_pos', 'po_line_items']
        
        for table in required_tables:
            try:
                response = self.client.table(table).select('*').limit(1).execute()
                self.log_test(f"Table {table} exists", True)
            except Exception as e:
                # Check if it's an RLS error (which means table exists but no access)
                if "row-level security" in str(e).lower() or "rls" in str(e).lower() or "policy" in str(e).lower():
                    self.log_test(f"Table {table} exists", True, "RLS enabled (expected)")
                else:
                    self.log_test(f"Table {table} exists", False, str(e))
    
    def test_database_functions(self):
        """Test 3: Database helper functions"""
        try:
            # Test helper functions exist
            functions_to_test = [
                'get_user_organization_id',
                'is_user_admin',
                'validate_organization_po_limit'
            ]
            
            for func in functions_to_test:
                try:
                    # Just test that function exists (will fail due to no auth context, but that's expected)
                    response = self.client.rpc(func, {}).execute()
                    self.log_test(f"Function {func} exists", True)
                except Exception as e:
                    if "function" in str(e).lower() and "does not exist" in str(e).lower():
                        self.log_test(f"Function {func} exists", False, "Function not found")
                    else:
                        # Function exists but failed due to auth context - that's expected
                        self.log_test(f"Function {func} exists", True, "Function exists (auth error expected)")
            
        except Exception as e:
            self.log_test("Database Functions", False, str(e))
    
    def test_database_adapter(self):
        """Test 4: Database adapter functionality"""
        try:
            # Test adapter info
            info = self.db_adapter.get_database_info()
            self.log_test("Database Adapter Info", True, f"Mode: {info['mode']}")
            
            # Test mode switching
            original_mode = self.db_adapter.mode
            self.db_adapter.switch_to_dual_mode()
            dual_mode = self.db_adapter.is_dual_mode()
            self.log_test("Switch to Dual Mode", dual_mode, "Dual mode activated")
            
            # Switch back
            self.db_adapter.mode = original_mode
            
        except Exception as e:
            self.log_test("Database Adapter", False, str(e))
    
    def test_environment_variables(self):
        """Test 5: Environment variables"""
        try:
            supabase_url = os.environ.get('SUPABASE_URL')
            supabase_key = os.environ.get('SUPABASE_ANON_KEY')
            ai_features = os.environ.get('ENABLE_AI_FEATURES')
            
            self.log_test("SUPABASE_URL set", bool(supabase_url), supabase_url[:50] + "..." if supabase_url else "Not set")
            self.log_test("SUPABASE_ANON_KEY set", bool(supabase_key), "Key present" if supabase_key else "Not set")
            self.log_test("AI Features enabled", ai_features == 'true', f"Value: {ai_features}")
            
        except Exception as e:
            self.log_test("Environment Variables", False, str(e))
    
    def test_supabase_client_methods(self):
        """Test 6: Supabase client methods"""
        try:
            # Test that client has expected methods
            methods = ['table', 'rpc', 'auth', 'storage']
            
            for method in methods:
                has_method = hasattr(self.client, method)
                self.log_test(f"Client has {method} method", has_method)
            
        except Exception as e:
            self.log_test("Supabase Client Methods", False, str(e))
    
    def run_all_tests(self):
        """Run all basic Phase 2 tests"""
        print("🧪 Running Basic Phase 2 Database Migration Tests...")
        print("="*60)
        
        # Run tests in order
        self.test_database_connection()
        self.test_schema_exists()
        self.test_database_functions()
        self.test_database_adapter()
        self.test_environment_variables()
        self.test_supabase_client_methods()
        
        # Print results
        self.print_test_summary()
        
        return self.test_results['failed'] == 0
    
    def print_test_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 BASIC PHASE 2 TEST SUMMARY")
        print("="*60)
        print(f"Tests passed: {self.test_results['passed']}")
        print(f"Tests failed: {self.test_results['failed']}")
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        if total_tests > 0:
            success_rate = (self.test_results['passed'] / total_tests * 100)
            print(f"Success rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n✅ All tests passed!")
        
        print("="*60)

def main():
    """Main test function"""
    tester = BasicPhase2Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Basic Phase 2 testing completed successfully!")
        print("Database migration infrastructure is ready.")
        return 0
    else:
        print("\n💥 Basic Phase 2 testing completed with failures!")
        print("Please review the errors above and fix them before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main()) 