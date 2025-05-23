from app import db
import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User model for authentication and row-level security"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Define relationships
    price_books = db.relationship('PriceBook', backref='owner', lazy='dynamic')
    processed_pos = db.relationship('ProcessedPO', backref='owner', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class PriceBook(db.Model):
    """Model for price books"""
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Define relationship with PriceItem
    items = db.relationship('PriceItem', backref='price_book', cascade='all, delete-orphan')
    
    # We create a composite unique constraint instead of just on name
    # This allows different users to have price books with the same name
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='_user_pricebook_uc'),
    )
    
    def __repr__(self):
        return f'<PriceBook {self.name}>'


class PriceItem(db.Model):
    """Model for individual price items in a price book"""
    id = db.Column(db.Integer, primary_key=True)
    model_number = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    price_book_id = db.Column(db.String(36), db.ForeignKey('price_book.id'), nullable=False)
    source_column = db.Column(db.String(10), nullable=True)  # Track which column the price came from
    excel_row = db.Column(db.Integer, nullable=True)  # Track Excel row number
    
    # Create an index on model_number and price_book_id for faster lookups
    __table_args__ = (
        db.Index('idx_model_pricebook', 'model_number', 'price_book_id'),
    )
    
    def __repr__(self):
        return f'<PriceItem {self.model_number} ${self.price}>'


class ProcessedPO(db.Model):
    """Model to store processed purchase orders"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    price_book_id = db.Column(db.String(36), db.ForeignKey('price_book.id'), nullable=False)
    processed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Define relationship with PriceBook
    price_book = db.relationship('PriceBook')
    
    # Define relationship with POLineItem
    line_items = db.relationship('POLineItem', backref='processed_po', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ProcessedPO {self.id} {self.filename}>'


class POLineItem(db.Model):
    """Model for line items in a processed purchase order"""
    id = db.Column(db.Integer, primary_key=True)
    processed_po_id = db.Column(db.Integer, db.ForeignKey('processed_po.id'), nullable=False)
    model_number = db.Column(db.String(100), nullable=False)
    po_price = db.Column(db.Float, nullable=False)
    book_price = db.Column(db.Float, nullable=True)  # Null if model not found in price book
    status = db.Column(db.String(50), nullable=False)  # "Match", "Mismatch", "Model Not Found", "Data Extraction Issue"
    discrepancy = db.Column(db.Float, nullable=True)  # Price difference (if mismatch)
    
    def __repr__(self):
        return f'<POLineItem {self.model_number} ${self.po_price} - {self.status}>'