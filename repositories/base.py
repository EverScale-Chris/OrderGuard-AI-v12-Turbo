"""
Base repository class for Supabase operations
Provides common CRUD operations with RLS support
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from uuid import UUID
from utils.supabase_client import get_supabase_client
from utils.db_adapter import get_db_adapter

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository for Supabase operations with RLS support"""
    
    def __init__(self, table_name: str, model_class: type):
        self.table_name = table_name
        self.model_class = model_class
        self.client = get_supabase_client()
        self.db_adapter = get_db_adapter()
    
    def create(self, data: dict) -> Optional[T]:
        """Create a new record"""
        try:
            self.db_adapter.log_operation(f"CREATE {self.table_name}", "supabase")
            response = self.client.table(self.table_name).insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return self.model_class.from_dict(response.data[0])
            return None
        except Exception as e:
            print(f"Error creating {self.table_name}: {e}")
            return None
    
    def get_by_id(self, id: UUID) -> Optional[T]:
        """Get record by ID (respects RLS)"""
        try:
            self.db_adapter.log_operation(f"GET {self.table_name} by ID", "supabase")
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq('id', str(id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                return self.model_class.from_dict(response.data[0])
            return None
        except Exception as e:
            print(f"Error getting {self.table_name} by ID: {e}")
            return None
    
    def get_all(self, filters: Dict[str, Any] = None, limit: int = None) -> List[T]:
        """Get all records with optional filters (respects RLS)"""
        try:
            self.db_adapter.log_operation(f"GET ALL {self.table_name}", "supabase")
            query = self.client.table(self.table_name).select("*")
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, UUID):
                        value = str(value)
                    query = query.eq(key, value)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            if response.data:
                return [self.model_class.from_dict(item) for item in response.data]
            return []
        except Exception as e:
            print(f"Error getting all {self.table_name}: {e}")
            return []
    
    def update(self, id: UUID, data: dict) -> Optional[T]:
        """Update a record (respects RLS)"""
        try:
            self.db_adapter.log_operation(f"UPDATE {self.table_name}", "supabase")
            response = self.client.table(self.table_name)\
                .update(data)\
                .eq('id', str(id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                return self.model_class.from_dict(response.data[0])
            return None
        except Exception as e:
            print(f"Error updating {self.table_name}: {e}")
            return None
    
    def delete(self, id: UUID) -> bool:
        """Delete a record (respects RLS)"""
        try:
            self.db_adapter.log_operation(f"DELETE {self.table_name}", "supabase")
            response = self.client.table(self.table_name)\
                .delete()\
                .eq('id', str(id))\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error deleting {self.table_name}: {e}")
            return False
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filters (respects RLS)"""
        try:
            self.db_adapter.log_operation(f"COUNT {self.table_name}", "supabase")
            query = self.client.table(self.table_name).select("id", count="exact")
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, UUID):
                        value = str(value)
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            print(f"Error counting {self.table_name}: {e}")
            return 0
    
    def exists(self, id: UUID) -> bool:
        """Check if record exists (respects RLS)"""
        try:
            record = self.get_by_id(id)
            return record is not None
        except Exception as e:
            print(f"Error checking existence in {self.table_name}: {e}")
            return False
    
    def bulk_create(self, data_list: List[dict]) -> List[T]:
        """Create multiple records in a single operation"""
        try:
            self.db_adapter.log_operation(f"BULK CREATE {self.table_name}", "supabase")
            response = self.client.table(self.table_name).insert(data_list).execute()
            
            if response.data:
                return [self.model_class.from_dict(item) for item in response.data]
            return []
        except Exception as e:
            print(f"Error bulk creating {self.table_name}: {e}")
            return [] 