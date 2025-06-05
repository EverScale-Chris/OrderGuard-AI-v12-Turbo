-- OrderGuard AI Pro - Initial Schema Migration
-- Migrates SQLAlchemy models to Supabase with multi-tenancy support
-- Date: January 6, 2025

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Organizations table (new for multi-tenancy and SaaS)
CREATE TABLE organizations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    subscription_status VARCHAR(50) DEFAULT 'trial',
    subscription_plan VARCHAR(50) DEFAULT 'starter',
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    trial_ends_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '14 days'),
    monthly_po_limit INTEGER DEFAULT 50, -- Starter plan limit
    monthly_po_count INTEGER DEFAULT 0,
    reset_date DATE DEFAULT (CURRENT_DATE + INTERVAL '1 month'),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table (modified for Supabase Auth integration)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- 'admin', 'member'
    is_admin BOOLEAN DEFAULT false, -- Keep compatibility with existing model
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure email uniqueness within organization
    UNIQUE(organization_id, email)
);

-- Price books table (enhanced with organization support)
CREATE TABLE price_books (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Keep reference to creator
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint: price book name per organization
    UNIQUE(organization_id, name)
);

-- Price items table (unchanged structure, inherits org from price_book)
CREATE TABLE price_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    price_book_id UUID REFERENCES price_books(id) ON DELETE CASCADE NOT NULL,
    model_number VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL, -- Changed from FLOAT for precision
    source_column VARCHAR(100),
    excel_row INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processed POs table (enhanced with organization support)
CREATE TABLE processed_pos (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    price_book_id UUID REFERENCES price_books(id) ON DELETE RESTRICT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Keep reference to processor
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PO line items table (unchanged structure)
CREATE TABLE po_line_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    processed_po_id UUID REFERENCES processed_pos(id) ON DELETE CASCADE NOT NULL,
    model_number VARCHAR(100) NOT NULL,
    po_price DECIMAL(10, 2) NOT NULL, -- Changed from FLOAT for precision
    book_price DECIMAL(10, 2), -- Null if model not found in price book
    status VARCHAR(50) NOT NULL, -- "Match", "Mismatch", "Model Not Found", "Data Extraction Issue"
    discrepancy DECIMAL(10, 2), -- Price difference (if mismatch)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_price_books_organization ON price_books(organization_id);
CREATE INDEX idx_price_books_user ON price_books(user_id);
CREATE INDEX idx_price_items_model_book ON price_items(model_number, price_book_id);
CREATE INDEX idx_price_items_price_book ON price_items(price_book_id);
CREATE INDEX idx_processed_pos_organization ON processed_pos(organization_id);
CREATE INDEX idx_processed_pos_user ON processed_pos(user_id);
CREATE INDEX idx_processed_pos_date ON processed_pos(processed_at);
CREATE INDEX idx_po_line_items_processed_po ON po_line_items(processed_po_id);
CREATE INDEX idx_po_line_items_status ON po_line_items(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_books_updated_at BEFORE UPDATE ON price_books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create helper functions for data validation
CREATE OR REPLACE FUNCTION validate_organization_po_limit(org_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    org_record organizations;
BEGIN
    SELECT * INTO org_record FROM organizations WHERE id = org_id;
    
    -- Check if organization exists and is active
    IF NOT FOUND OR NOT org_record.is_active THEN
        RETURN FALSE;
    END IF;
    
    -- Check monthly limit (unlimited for enterprise)
    IF org_record.subscription_plan = 'enterprise' THEN
        RETURN TRUE;
    END IF;
    
    -- Reset counter if needed
    IF org_record.reset_date <= CURRENT_DATE THEN
        UPDATE organizations 
        SET monthly_po_count = 0, 
            reset_date = CURRENT_DATE + INTERVAL '1 month'
        WHERE id = org_id;
        RETURN TRUE;
    END IF;
    
    -- Check if under limit
    RETURN org_record.monthly_po_count < org_record.monthly_po_limit;
END;
$$ LANGUAGE plpgsql; 