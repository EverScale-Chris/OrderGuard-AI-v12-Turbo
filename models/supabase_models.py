"""
Supabase data models for OrderGuard AI Pro
Corresponds to the multi-tenant schema with organizations
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from decimal import Decimal

@dataclass
class Organization:
    """Organization model for multi-tenancy"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    subscription_status: str = "trial"
    subscription_plan: str = "starter"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    monthly_po_limit: int = 50
    monthly_po_count: int = 0
    reset_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'subscription_status': self.subscription_status,
            'subscription_plan': self.subscription_plan,
            'stripe_customer_id': self.stripe_customer_id,
            'stripe_subscription_id': self.stripe_subscription_id,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'monthly_po_limit': self.monthly_po_limit,
            'monthly_po_count': self.monthly_po_count,
            'reset_date': self.reset_date.isoformat() if self.reset_date else None,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Organization':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']) if data.get('id') else uuid4(),
            name=data.get('name', ''),
            slug=data.get('slug', ''),
            subscription_status=data.get('subscription_status', 'trial'),
            subscription_plan=data.get('subscription_plan', 'starter'),
            stripe_customer_id=data.get('stripe_customer_id'),
            stripe_subscription_id=data.get('stripe_subscription_id'),
            trial_ends_at=datetime.fromisoformat(data['trial_ends_at'].replace('Z', '+00:00')) if data.get('trial_ends_at') else None,
            monthly_po_limit=data.get('monthly_po_limit', 50),
            monthly_po_count=data.get('monthly_po_count', 0),
            reset_date=datetime.fromisoformat(data['reset_date']) if data.get('reset_date') else None,
            is_active=data.get('is_active', True),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
        )

@dataclass
class User:
    """User model for Supabase Auth integration"""
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    email: str = ""
    username: str = ""
    role: str = "member"
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'organization_id': str(self.organization_id),
            'email': self.email,
            'username': self.username,
            'role': self.role,
            'is_admin': self.is_admin,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']),
            organization_id=UUID(data['organization_id']),
            email=data.get('email', ''),
            username=data.get('username', ''),
            role=data.get('role', 'member'),
            is_admin=data.get('is_admin', False),
            is_active=data.get('is_active', True),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
        )

@dataclass
class PriceBook:
    """Price book model with organization support"""
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    name: str = ""
    user_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'organization_id': str(self.organization_id),
            'name': self.name,
            'user_id': str(self.user_id) if self.user_id else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PriceBook':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']),
            organization_id=UUID(data['organization_id']),
            name=data.get('name', ''),
            user_id=UUID(data['user_id']) if data.get('user_id') else None,
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
        )

@dataclass
class PriceItem:
    """Price item model"""
    id: UUID = field(default_factory=uuid4)
    price_book_id: UUID = field(default_factory=uuid4)
    model_number: str = ""
    price: Decimal = field(default_factory=lambda: Decimal('0.00'))
    source_column: Optional[str] = None
    excel_row: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'price_book_id': str(self.price_book_id),
            'model_number': self.model_number,
            'price': float(self.price),
            'source_column': self.source_column,
            'excel_row': self.excel_row
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PriceItem':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']),
            price_book_id=UUID(data['price_book_id']),
            model_number=data.get('model_number', ''),
            price=Decimal(str(data.get('price', '0.00'))),
            source_column=data.get('source_column'),
            excel_row=data.get('excel_row'),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None
        )

@dataclass
class ProcessedPO:
    """Processed PO model with organization support"""
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    filename: str = ""
    price_book_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    processed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'organization_id': str(self.organization_id),
            'filename': self.filename,
            'price_book_id': str(self.price_book_id),
            'user_id': str(self.user_id) if self.user_id else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedPO':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']),
            organization_id=UUID(data['organization_id']),
            filename=data.get('filename', ''),
            price_book_id=UUID(data['price_book_id']),
            user_id=UUID(data['user_id']) if data.get('user_id') else None,
            processed_at=datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00')) if data.get('processed_at') else None
        )

@dataclass
class POLineItem:
    """PO line item model"""
    id: UUID = field(default_factory=uuid4)
    processed_po_id: UUID = field(default_factory=uuid4)
    model_number: str = ""
    po_price: Decimal = field(default_factory=lambda: Decimal('0.00'))
    book_price: Optional[Decimal] = None
    status: str = ""
    discrepancy: Optional[Decimal] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Supabase operations"""
        return {
            'id': str(self.id),
            'processed_po_id': str(self.processed_po_id),
            'model_number': self.model_number,
            'po_price': float(self.po_price),
            'book_price': float(self.book_price) if self.book_price else None,
            'status': self.status,
            'discrepancy': float(self.discrepancy) if self.discrepancy else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'POLineItem':
        """Create from dictionary (from Supabase)"""
        return cls(
            id=UUID(data['id']),
            processed_po_id=UUID(data['processed_po_id']),
            model_number=data.get('model_number', ''),
            po_price=Decimal(str(data.get('po_price', '0.00'))),
            book_price=Decimal(str(data['book_price'])) if data.get('book_price') else None,
            status=data.get('status', ''),
            discrepancy=Decimal(str(data['discrepancy'])) if data.get('discrepancy') else None,
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None
        ) 