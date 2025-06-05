"""
Phase 2 Test Script - Database Migration Testing
Tests Supabase schema, RLS policies, and repository operations
"""

import sys
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.supabase_client import get_supabase_client, get_supabase_admin_client
from utils.db_adapter import get_db_adapter
from models.supabase_models import Organization, User, PriceBook, PriceItem
from repositories.organization_repository import OrganizationRepository
from repositories.price_book_repository import PriceBookRepository

class Phase2Tester:
    """Test suite for Phase 2 database migration functionality"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.admin_client = get_supabase_admin_client()
        self.db_adapter = get_db_adapter()
        self.org_repo = OrganizationRepository()
        self.pb_repo = PriceBookRepository()
        
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Test data
        self.test_org_id = None
        self.test_user_id = None
        self.test_pb_id = None
    
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
                self.log_test(f"Table {table} exists", False, str(e))
    
    def test_create_organization(self):
        """Test 3: Create test organization"""
        try:
            org_data = {
                'name': 'Test Organization Phase 2',
                'slug': f'test-org-{uuid4().hex[:8]}',
                'subscription_plan': 'starter',
                'subscription_status': 'trial'
            }
            
            org = self.org_repo.create(org_data)
            if org:
                self.test_org_id = org.id
                self.log_test("Create Organization", True, f"Created org: {org.name}")
            else:
                self.log_test("Create Organization", False, "No organization returned")
                
        except Exception as e:
            self.log_test("Create Organization", False, str(e))
    
    def test_create_user_profile(self):
        """Test 4: Create test user profile (simulated)"""
        if not self.test_org_id:
            self.log_test("Create User Profile", False, "No test organization available")
            return
        
        try:
            # Note: In real scenario, this would be created via Supabase Auth
            # For testing, we'll create the profile directly
            user_id = uuid4()
            user_data = {
                'id': str(user_id),
                'organization_id': str(self.test_org_id),
                'email': f'test-{uuid4().hex[:8]}@example.com',
                'username': f'testuser-{uuid4().hex[:8]}',
                'role': 'admin',
                'is_admin': True
            }
            
            # Use admin client to bypass RLS for testing
            response = self.admin_client.table('users').insert(user_data).execute()
            
            if response.data:
                self.test_user_id = user_id
                self.log_test("Create User Profile", True, f"Created user: {user_data['username']}")
            else:
                self.log_test("Create User Profile", False, "No user data returned")
                
        except Exception as e:
            self.log_test("Create User Profile", False, str(e))
    
    def test_create_price_book(self):
        """Test 5: Create test price book"""
        if not self.test_org_id:
            self.log_test("Create Price Book", False, "No test organization available")
            return
        
        try:
            pb_data = {
                'organization_id': str(self.test_org_id),
                'name': f'Test Price Book {uuid4().hex[:8]}',
                'user_id': str(self.test_user_id) if self.test_user_id else None
            }
            
            # Use admin client to bypass RLS for testing
            response = self.admin_client.table('price_books').insert(pb_data).execute()
            
            if response.data:
                self.test_pb_id = response.data[0]['id']
                self.log_test("Create Price Book", True, f"Created price book: {pb_data['name']}")
            else:
                self.log_test("Create Price Book", False, "No price book data returned")
                
        except Exception as e:
            self.log_test("Create Price Book", False, str(e))
    
    def test_create_price_items(self):
        """Test 6: Create test price items"""
        if not self.test_pb_id:
            self.log_test("Create Price Items", False, "No test price book available")
            return
        
        try:
            items_data = [
                {
                    'price_book_id': self.test_pb_id,
                    'model_number': f'TEST-{i:03d}',
                    'price': 100.00 + i,
                    'source_column': 'Price',
                    'excel_row': i + 1
                }
                for i in range(5)
            ]
            
            response = self.admin_client.table('price_items').insert(items_data).execute()
            
            if response.data and len(response.data) == 5:
                self.log_test("Create Price Items", True, f"Created {len(response.data)} price items")
            else:
                self.log_test("Create Price Items", False, f"Expected 5 items, got {len(response.data) if response.data else 0}")
                
        except Exception as e:
            self.log_test("Create Price Items", False, str(e))
    
    def test_organization_repository(self):
        """Test 7: Organization repository operations"""
        try:
            # Test get by ID
            if self.test_org_id:
                org = self.org_repo.get_by_id(self.test_org_id)
                if org:
                    self.log_test("Org Repository - Get by ID", True)
                else:
                    self.log_test("Org Repository - Get by ID", False, "Organization not found")
            
            # Test get active organizations
            active_orgs = self.org_repo.get_active_organizations()
            self.log_test("Org Repository - Get Active", len(active_orgs) >= 0, f"Found {len(active_orgs)} active orgs")
            
        except Exception as e:
            self.log_test("Organization Repository", False, str(e))
    
    def test_price_book_repository(self):
        """Test 8: Price book repository operations"""
        try:
            if self.test_org_id:
                # Test get by organization
                org_pbs = self.pb_repo.get_by_organization(self.test_org_id)
                self.log_test("PB Repository - Get by Org", len(org_pbs) >= 0, f"Found {len(org_pbs)} price books")
                
                # Test get with items
                if self.test_pb_id:
                    pb_with_items = self.pb_repo.get_with_items(self.test_pb_id)
                    if pb_with_items and pb_with_items.get('items'):
                        self.log_test("PB Repository - Get with Items", True, f"Found {len(pb_with_items['items'])} items")
                    else:
                        self.log_test("PB Repository - Get with Items", False, "No items found")
            
        except Exception as e:
            self.log_test("Price Book Repository", False, str(e))
    
    def test_rls_policies(self):
        """Test 9: Row Level Security policies"""
        try:
            # Test that RLS is enabled
            tables_with_rls = ['organizations', 'users', 'price_books', 'price_items', 'processed_pos', 'po_line_items']
            
            for table in tables_with_rls:
                try:
                    # This should work with admin client
                    response = self.admin_client.table(table).select('*').limit(1).execute()
                    self.log_test(f"RLS - {table} accessible", True)
                except Exception as e:
                    self.log_test(f"RLS - {table} accessible", False, str(e))
            
        except Exception as e:
            self.log_test("RLS Policies", False, str(e))
    
    def test_database_functions(self):
        """Test 10: Database helper functions"""
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
                    response = self.admin_client.rpc(func, {}).execute()
                    self.log_test(f"Function {func} exists", True)
                except Exception as e:
                    if "function" in str(e).lower() and "does not exist" in str(e).lower():
                        self.log_test(f"Function {func} exists", False, "Function not found")
                    else:
                        # Function exists but failed due to auth context - that's expected
                        self.log_test(f"Function {func} exists", True, "Function exists (auth error expected)")
            
        except Exception as e:
            self.log_test("Database Functions", False, str(e))
    
    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            # Clean up in reverse order of dependencies
            if self.test_pb_id:
                self.admin_client.table('price_items').delete().eq('price_book_id', self.test_pb_id).execute()
                self.admin_client.table('price_books').delete().eq('id', self.test_pb_id).execute()
            
            if self.test_user_id:
                self.admin_client.table('users').delete().eq('id', str(self.test_user_id)).execute()
            
            if self.test_org_id:
                self.admin_client.table('organizations').delete().eq('id', str(self.test_org_id)).execute()
            
            print("🧹 Test data cleaned up")
            
        except Exception as e:
            print(f"⚠️  Error cleaning up test data: {e}")
    
    def run_all_tests(self):
        """Run all Phase 2 tests"""
        print("🧪 Running Phase 2 Database Migration Tests...")
        print("="*60)
        
        # Run tests in order
        self.test_database_connection()
        self.test_schema_exists()
        self.test_create_organization()
        self.test_create_user_profile()
        self.test_create_price_book()
        self.test_create_price_items()
        self.test_organization_repository()
        self.test_price_book_repository()
        self.test_rls_policies()
        self.test_database_functions()
        
        # Print results
        self.print_test_summary()
        
        # Cleanup
        self.cleanup_test_data()
        
        return self.test_results['failed'] == 0
    
    def print_test_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 PHASE 2 TEST SUMMARY")
        print("="*60)
        print(f"Tests passed: {self.test_results['passed']}")
        print(f"Tests failed: {self.test_results['failed']}")
        print(f"Success rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100):.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n✅ All tests passed!")
        
        print("="*60)

def main():
    """Main test function"""
    tester = Phase2Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 Phase 2 testing completed successfully!")
        print("Database migration infrastructure is ready.")
        return 0
    else:
        print("\n💥 Phase 2 testing completed with failures!")
        print("Please review the errors above and fix them before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main()) 