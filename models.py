from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    roast = Column(String(50))
    notes = Column(Text)
    allergens = Column(JSON)  # Store as JSON array
    caffeine_mg = Column(Integer)
    vendor = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    interactions = relationship('ProductInteraction', back_populates='product', cascade='all, delete-orphan')

class CustomerAccount(Base):
    __tablename__ = 'customer_accounts'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    allergies = Column(JSON)  # Store as JSON array
    avoid_list = Column(JSON)  # Store as JSON array
    liked_drinks = Column(JSON)  # Store as JSON array
    disliked_drinks = Column(JSON)  # Store as JSON array
    preferred_vendors = Column(JSON)  # Store as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VendorAccount(Base):
    __tablename__ = 'vendor_accounts'
    
    id = Column(Integer, primary_key=True)
    business_name = Column(String(255), unique=True, nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    facebook_business_id = Column(String(255))
    status = Column(String(50), default='pending')  # pending, approved, rejected, blocked, suspended
    reject_reason = Column(Text)
    block_reason = Column(Text)
    suspend_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductInteraction(Base):
    __tablename__ = 'product_interactions'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    interaction_type = Column(String(20), nullable=False)  # 'like' or 'dislike'
    customer_email = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    product = relationship('Product', back_populates='interactions')

class AdminAccount(Base):
    __tablename__ = 'admin_accounts'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # In production, use hashed passwords!
    role = Column(String(50), default='admin')  # admin, super_admin
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database connection setup
def get_database_url():
    """Get database URL from environment or use default"""
    return os.environ.get('DATABASE_URL', 'postgresql://localhost/satisfy')

def init_db_engine(database_url=None):
    """Initialize database engine and session maker"""
    if database_url is None:
        database_url = get_database_url()
    
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal

def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)
