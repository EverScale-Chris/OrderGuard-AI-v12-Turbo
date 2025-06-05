"""
Migration script to transfer data from SQLAlchemy to Supabase
Handles the data migration while maintaining referential integrity
"""

import sys
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

print("🚀 Starting OrderGuard AI Pro Data Migration...")
print("This script will migrate data from SQLAlchemy to Supabase")
print("="*60)

from app import app, db
from models import User as SQLUser, PriceBook as SQLPriceBook, PriceItem as SQLPriceItem, ProcessedPO as SQLProcessedPO, POLineItem as SQLPOLineItem
from models.supabase_models import Organization, User, PriceBook, PriceItem, ProcessedPO, POLineItem
from repositories.organization_repository import OrganizationRepository
from repositories.price_book_repository import PriceBookRepository
from utils.supabase_client import get_supabase_admin_client
from utils.db_adapter import get_db_adapter

class DataMigrator:
    """Handles data migration from SQLAlchemy to Supabase"""
    
    def __init__(self):
        self.client = get_supabase_admin_client()
        self.db_adapter = get_db_adapter()
        self.org_repo = OrganizationRepository()
        self.price_book_repo = PriceBookRepository()
        
        # Migration tracking
        self.migration_stats = {
            'organizations_created': 0,
            'users_migrated': 0,
            'price_books_migrated': 0,
            'price_items_migrated': 0,
            'processed_pos_migrated': 0,
            'po_line_items_migrated': 0,
            'errors': []
        }
        
        # ID mapping for foreign key relationships
        self.user_id_mapping = {}  # SQLAlchemy ID -> Supabase UUID
        self.price_book_id_mapping = {}  # SQLAlchemy ID -> Supabase UUID
        self.processed_po_id_mapping = {}  # SQLAlchemy ID -> Supabase UUID
    
    def create_default_organization(self) -> Organization:
        """Create a default organization for existing users"""
        try:
            org_data = {
                'id': str(uuid4()),
                'name': 'OrderGuard Legacy Organization',
                'slug': 'orderguard-legacy',
                'subscription_status': 'active',
                'subscription_plan': 'professional',  # Give existing users professional plan
                'monthly_po_limit': 200,
                'monthly_po_count': 0,
                'is_active': True
            }
            
            org = self.org_repo.create(org_data)
            if org:
                self.migration_stats['organizations_created'] += 1
                print(f"✅ Created default organization: {org.name}")
                return org
            else:
                raise Exception("Failed to create default organization")
                
        except Exception as e:
            error_msg = f"Error creating default organization: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return None
    
    def migrate_users(self, default_org: Organization):
        """Migrate users from SQLAlchemy to Supabase"""
        print("\n🔄 Migrating users...")
        
        try:
            with app.app_context():
                sql_users = SQLUser.query.all()
                print(f"Found {len(sql_users)} users to migrate")
                
                for sql_user in sql_users:
                    try:
                        # Generate new UUID for Supabase
                        new_user_id = uuid4()
                        
                        # Note: In real migration, you'd need to handle Supabase Auth user creation
                        # For now, we'll create the profile record assuming Auth user exists
                        user_data = {
                            'id': str(new_user_id),
                            'organization_id': str(default_org.id),
                            'email': sql_user.email,
                            'username': sql_user.username,
                            'role': 'admin' if sql_user.is_admin else 'member',
                            'is_admin': sql_user.is_admin,
                            'is_active': True
                        }
                        
                        # Insert directly using client (bypassing RLS for migration)
                        response = self.client.table('users').insert(user_data).execute()
                        
                        if response.data:
                            # Store mapping for foreign key relationships
                            self.user_id_mapping[sql_user.id] = new_user_id
                            self.migration_stats['users_migrated'] += 1
                            print(f"  ✅ Migrated user: {sql_user.username}")
                        else:
                            raise Exception("No data returned from insert")
                            
                    except Exception as e:
                        error_msg = f"Error migrating user {sql_user.username}: {e}"
                        self.migration_stats['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                        
        except Exception as e:
            error_msg = f"Error in user migration: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def migrate_price_books(self, default_org: Organization):
        """Migrate price books from SQLAlchemy to Supabase"""
        print("\n🔄 Migrating price books...")
        
        try:
            with app.app_context():
                sql_price_books = SQLPriceBook.query.all()
                print(f"Found {len(sql_price_books)} price books to migrate")
                
                for sql_pb in sql_price_books:
                    try:
                        new_pb_id = uuid4()
                        
                        # Map user ID
                        user_uuid = self.user_id_mapping.get(sql_pb.user_id)
                        
                        price_book_data = {
                            'id': str(new_pb_id),
                            'organization_id': str(default_org.id),
                            'name': sql_pb.name,
                            'user_id': str(user_uuid) if user_uuid else None
                        }
                        
                        response = self.client.table('price_books').insert(price_book_data).execute()
                        
                        if response.data:
                            self.price_book_id_mapping[sql_pb.id] = new_pb_id
                            self.migration_stats['price_books_migrated'] += 1
                            print(f"  ✅ Migrated price book: {sql_pb.name}")
                            
                            # Migrate associated price items
                            self.migrate_price_items(sql_pb, new_pb_id)
                        else:
                            raise Exception("No data returned from insert")
                            
                    except Exception as e:
                        error_msg = f"Error migrating price book {sql_pb.name}: {e}"
                        self.migration_stats['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                        
        except Exception as e:
            error_msg = f"Error in price book migration: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def migrate_price_items(self, sql_price_book, new_pb_id):
        """Migrate price items for a specific price book"""
        try:
            sql_items = SQLPriceItem.query.filter_by(price_book_id=sql_price_book.id).all()
            
            if not sql_items:
                return
            
            items_data = []
            for sql_item in sql_items:
                item_data = {
                    'id': str(uuid4()),
                    'price_book_id': str(new_pb_id),
                    'model_number': sql_item.model_number,
                    'price': float(sql_item.price),
                    'source_column': sql_item.source_column,
                    'excel_row': sql_item.excel_row
                }
                items_data.append(item_data)
            
            # Bulk insert items
            response = self.client.table('price_items').insert(items_data).execute()
            
            if response.data:
                self.migration_stats['price_items_migrated'] += len(response.data)
                print(f"    ✅ Migrated {len(response.data)} price items")
            
        except Exception as e:
            error_msg = f"Error migrating price items for {sql_price_book.name}: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"    ❌ {error_msg}")
    
    def migrate_processed_pos(self, default_org: Organization):
        """Migrate processed POs from SQLAlchemy to Supabase"""
        print("\n🔄 Migrating processed POs...")
        
        try:
            with app.app_context():
                sql_pos = SQLProcessedPO.query.all()
                print(f"Found {len(sql_pos)} processed POs to migrate")
                
                for sql_po in sql_pos:
                    try:
                        new_po_id = uuid4()
                        
                        # Map foreign keys
                        user_uuid = self.user_id_mapping.get(sql_po.user_id)
                        pb_uuid = self.price_book_id_mapping.get(sql_po.price_book_id)
                        
                        if not pb_uuid:
                            print(f"  ⚠️  Skipping PO {sql_po.filename} - price book not found")
                            continue
                        
                        po_data = {
                            'id': str(new_po_id),
                            'organization_id': str(default_org.id),
                            'filename': sql_po.filename,
                            'price_book_id': str(pb_uuid),
                            'user_id': str(user_uuid) if user_uuid else None,
                            'processed_at': sql_po.processed_at.isoformat() if sql_po.processed_at else None
                        }
                        
                        response = self.client.table('processed_pos').insert(po_data).execute()
                        
                        if response.data:
                            self.processed_po_id_mapping[sql_po.id] = new_po_id
                            self.migration_stats['processed_pos_migrated'] += 1
                            print(f"  ✅ Migrated PO: {sql_po.filename}")
                            
                            # Migrate line items
                            self.migrate_po_line_items(sql_po, new_po_id)
                        else:
                            raise Exception("No data returned from insert")
                            
                    except Exception as e:
                        error_msg = f"Error migrating PO {sql_po.filename}: {e}"
                        self.migration_stats['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                        
        except Exception as e:
            error_msg = f"Error in processed PO migration: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def migrate_po_line_items(self, sql_po, new_po_id):
        """Migrate line items for a specific processed PO"""
        try:
            sql_line_items = SQLPOLineItem.query.filter_by(processed_po_id=sql_po.id).all()
            
            if not sql_line_items:
                return
            
            line_items_data = []
            for sql_item in sql_line_items:
                item_data = {
                    'id': str(uuid4()),
                    'processed_po_id': str(new_po_id),
                    'model_number': sql_item.model_number,
                    'po_price': float(sql_item.po_price),
                    'book_price': float(sql_item.book_price) if sql_item.book_price else None,
                    'status': sql_item.status,
                    'discrepancy': float(sql_item.discrepancy) if sql_item.discrepancy else None
                }
                line_items_data.append(item_data)
            
            # Bulk insert line items
            response = self.client.table('po_line_items').insert(line_items_data).execute()
            
            if response.data:
                self.migration_stats['po_line_items_migrated'] += len(response.data)
                print(f"    ✅ Migrated {len(response.data)} line items")
            
        except Exception as e:
            error_msg = f"Error migrating line items for {sql_po.filename}: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"    ❌ {error_msg}")
    
    def run_migration(self):
        """Run the complete migration process"""
        print("🚀 Starting data migration from SQLAlchemy to Supabase...")
        print(f"Migration started at: {datetime.now()}")
        
        try:
            # Step 1: Create default organization
            default_org = self.create_default_organization()
            if not default_org:
                print("❌ Migration failed - could not create default organization")
                return False
            
            # Step 2: Migrate users
            self.migrate_users(default_org)
            
            # Step 3: Migrate price books and items
            self.migrate_price_books(default_org)
            
            # Step 4: Migrate processed POs and line items
            self.migrate_processed_pos(default_org)
            
            # Print migration summary
            self.print_migration_summary()
            
            return len(self.migration_stats['errors']) == 0
            
        except Exception as e:
            error_msg = f"Critical migration error: {e}"
            self.migration_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    def print_migration_summary(self):
        """Print migration statistics"""
        print("\n" + "="*60)
        print("📊 MIGRATION SUMMARY")
        print("="*60)
        print(f"Organizations created: {self.migration_stats['organizations_created']}")
        print(f"Users migrated: {self.migration_stats['users_migrated']}")
        print(f"Price books migrated: {self.migration_stats['price_books_migrated']}")
        print(f"Price items migrated: {self.migration_stats['price_items_migrated']}")
        print(f"Processed POs migrated: {self.migration_stats['processed_pos_migrated']}")
        print(f"PO line items migrated: {self.migration_stats['po_line_items_migrated']}")
        print(f"Errors encountered: {len(self.migration_stats['errors'])}")
        
        if self.migration_stats['errors']:
            print("\n❌ ERRORS:")
            for error in self.migration_stats['errors']:
                print(f"  - {error}")
        else:
            print("\n✅ Migration completed successfully with no errors!")
        
        print("="*60)

def main():
    """Main migration function"""
    migrator = DataMigrator()
    success = migrator.run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now switch to dual database mode.")
        return 0
    else:
        print("\n💥 Migration completed with errors!")
        print("Please review the errors above and fix them before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main()) 