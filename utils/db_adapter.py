"""
Database Adapter for OrderGuard AI Pro Migration
Handles the transition from SQLAlchemy to Supabase with dual database strategy
"""

import os
from enum import Enum
from typing import Optional, Any, Dict
from dotenv import load_dotenv

load_dotenv()

class DatabaseMode(Enum):
    """Database mode enumeration"""
    SQLALCHEMY = "sqlalchemy"
    SUPABASE = "supabase"
    DUAL = "dual"  # Both databases active

class DatabaseAdapter:
    """
    Database adapter to manage transition from SQLAlchemy to Supabase
    """
    
    def __init__(self):
        self.mode = DatabaseMode.SQLALCHEMY  # Start with existing SQLAlchemy
        self._vector_enabled = False
        self._edge_functions_enabled = False
        self._ai_features_enabled = self._check_ai_features()
        
    def _check_ai_features(self) -> bool:
        """Check if AI features are enabled in environment"""
        return os.environ.get('ENABLE_AI_FEATURES', 'false').lower() == 'true'
    
    def switch_to_dual_mode(self):
        """Switch to dual mode - both databases active"""
        self.mode = DatabaseMode.DUAL
        print("🔄 Switched to dual database mode")
        
    def switch_to_supabase(self):
        """Switch to Supabase mode completely"""
        self.mode = DatabaseMode.SUPABASE
        self._vector_enabled = True
        self._edge_functions_enabled = True
        print("✅ Switched to Supabase mode")
        
    def switch_to_sqlalchemy(self):
        """Switch back to SQLAlchemy mode (rollback)"""
        self.mode = DatabaseMode.SQLALCHEMY
        self._vector_enabled = False
        self._edge_functions_enabled = False
        print("🔙 Switched back to SQLAlchemy mode")
    
    def is_sqlalchemy_mode(self) -> bool:
        """Check if in SQLAlchemy mode"""
        return self.mode == DatabaseMode.SQLALCHEMY
    
    def is_supabase_mode(self) -> bool:
        """Check if in Supabase mode"""
        return self.mode == DatabaseMode.SUPABASE
    
    def is_dual_mode(self) -> bool:
        """Check if in dual mode"""
        return self.mode == DatabaseMode.DUAL
    
    def has_vector_support(self) -> bool:
        """Check if vector operations are available"""
        return self._vector_enabled and self._ai_features_enabled
    
    def has_edge_functions(self) -> bool:
        """Check if Edge Functions are available"""
        return self._edge_functions_enabled and self._ai_features_enabled
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get current database configuration info"""
        return {
            'mode': self.mode.value,
            'vector_enabled': self._vector_enabled,
            'edge_functions_enabled': self._edge_functions_enabled,
            'ai_features_enabled': self._ai_features_enabled,
            'supabase_url': os.environ.get('SUPABASE_URL'),
            'phase': self._get_migration_phase()
        }
    
    def _get_migration_phase(self) -> str:
        """Determine current migration phase based on configuration"""
        if self.mode == DatabaseMode.SQLALCHEMY:
            return "Phase 1 - Foundation Setup"
        elif self.mode == DatabaseMode.DUAL:
            return "Phase 2-4 - Migration in Progress"
        elif self.mode == DatabaseMode.SUPABASE:
            return "Phase 5+ - Supabase Native"
        else:
            return "Unknown Phase"
    
    def log_operation(self, operation: str, database: str = None):
        """Log database operations for monitoring during migration"""
        db_target = database or self.mode.value
        print(f"📊 DB Operation: {operation} on {db_target}")

# Global database adapter instance
db_adapter = DatabaseAdapter()

def get_db_adapter() -> DatabaseAdapter:
    """Get the global database adapter instance"""
    return db_adapter

def is_migration_phase() -> bool:
    """Quick check if we're in migration phase"""
    return db_adapter.is_dual_mode()

def can_use_ai_features() -> bool:
    """Quick check if AI features are available"""
    return db_adapter.has_vector_support() and db_adapter.has_edge_functions()

# Migration phase helpers
def enable_dual_mode():
    """Enable dual database mode for migration"""
    db_adapter.switch_to_dual_mode()

def complete_migration():
    """Complete migration to Supabase"""
    db_adapter.switch_to_supabase()

def rollback_migration():
    """Rollback to SQLAlchemy mode"""
    db_adapter.switch_to_sqlalchemy()

# Initialize
print(f"🔧 Database Adapter initialized in {db_adapter.mode.value} mode")
if db_adapter._ai_features_enabled:
    print("🤖 AI features enabled")
else:
    print("⚠️  AI features disabled (set ENABLE_AI_FEATURES=true to enable)") 