"""
Price Book Repository for Supabase operations
Handles price books with organization-level isolation
"""

from typing import List, Optional
from uuid import UUID
from repositories.base import BaseRepository
from models.supabase_models import PriceBook, PriceItem

class PriceBookRepository(BaseRepository[PriceBook]):
    """Repository for price book operations with RLS support"""
    
    def __init__(self):
        super().__init__('price_books', PriceBook)
    
    def get_by_organization(self, org_id: UUID) -> List[PriceBook]:
        """Get all price books for an organization"""
        return self.get_all({'organization_id': org_id})
    
    def get_by_name_and_org(self, name: str, org_id: UUID) -> Optional[PriceBook]:
        """Get price book by name within organization"""
        results = self.get_all({'name': name, 'organization_id': org_id})
        return results[0] if results else None
    
    def get_with_items(self, price_book_id: UUID) -> dict:
        """Get price book with all its items"""
        try:
            # Get price book
            price_book = self.get_by_id(price_book_id)
            if not price_book:
                return None
            
            # Get items using separate query
            items_response = self.client.table('price_items')\
                .select("*")\
                .eq('price_book_id', str(price_book_id))\
                .execute()
            
            items = []
            if items_response.data:
                items = [PriceItem.from_dict(item) for item in items_response.data]
            
            return {
                'price_book': price_book,
                'items': items,
                'item_count': len(items)
            }
        except Exception as e:
            print(f"Error getting price book with items: {e}")
            return None
    
    def create_with_items(self, price_book_data: dict, items_data: List[dict]) -> Optional[dict]:
        """Create price book and its items in a transaction"""
        try:
            # Create price book first
            price_book = self.create(price_book_data)
            if not price_book:
                return None
            
            # Add price_book_id to all items
            for item_data in items_data:
                item_data['price_book_id'] = str(price_book.id)
            
            # Create items in bulk
            items_response = self.client.table('price_items')\
                .insert(items_data)\
                .execute()
            
            items = []
            if items_response.data:
                items = [PriceItem.from_dict(item) for item in items_response.data]
            
            return {
                'price_book': price_book,
                'items': items,
                'item_count': len(items)
            }
        except Exception as e:
            print(f"Error creating price book with items: {e}")
            return None
    
    def get_user_price_books(self, user_id: UUID) -> List[PriceBook]:
        """Get price books created by a specific user"""
        return self.get_all({'user_id': user_id})
    
    def search_by_name(self, search_term: str, org_id: UUID) -> List[PriceBook]:
        """Search price books by name within organization"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq('organization_id', str(org_id))\
                .ilike('name', f'%{search_term}%')\
                .execute()
            
            if response.data:
                return [self.model_class.from_dict(item) for item in response.data]
            return []
        except Exception as e:
            print(f"Error searching price books: {e}")
            return []
    
    def get_recent(self, org_id: UUID, limit: int = 10) -> List[PriceBook]:
        """Get most recently created price books for organization"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq('organization_id', str(org_id))\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if response.data:
                return [self.model_class.from_dict(item) for item in response.data]
            return []
        except Exception as e:
            print(f"Error getting recent price books: {e}")
            return [] 