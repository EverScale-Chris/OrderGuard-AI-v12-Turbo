-- OrderGuard AI Pro - Row Level Security Policies
-- Ensures data isolation between organizations
-- Date: January 6, 2025

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_books ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_pos ENABLE ROW LEVEL SECURITY;
ALTER TABLE po_line_items ENABLE ROW LEVEL SECURITY;

-- Helper function to get user's organization ID
CREATE OR REPLACE FUNCTION auth.user_organization_id()
RETURNS UUID AS $$
BEGIN
    RETURN (
        SELECT organization_id 
        FROM users 
        WHERE id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to check if user is admin
CREATE OR REPLACE FUNCTION auth.is_user_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE((
        SELECT is_admin 
        FROM users 
        WHERE id = auth.uid()
    ), false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ORGANIZATIONS TABLE POLICIES
-- Users can only view their own organization
CREATE POLICY "Users can view their organization"
    ON organizations FOR SELECT
    USING (id = auth.user_organization_id());

-- Only admins can update organization settings
CREATE POLICY "Admins can update organization"
    ON organizations FOR UPDATE
    USING (id = auth.user_organization_id() AND auth.is_user_admin())
    WITH CHECK (id = auth.user_organization_id() AND auth.is_user_admin());

-- USERS TABLE POLICIES
-- Users can view members of their organization
CREATE POLICY "Users can view organization members"
    ON users FOR SELECT
    USING (organization_id = auth.user_organization_id());

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- Admins can manage organization users
CREATE POLICY "Admins can manage organization users"
    ON users FOR ALL
    USING (organization_id = auth.user_organization_id() AND auth.is_user_admin())
    WITH CHECK (organization_id = auth.user_organization_id() AND auth.is_user_admin());

-- PRICE BOOKS TABLE POLICIES
-- Users can view organization price books
CREATE POLICY "Users can view organization price books"
    ON price_books FOR SELECT
    USING (organization_id = auth.user_organization_id());

-- Users can create price books in their organization
CREATE POLICY "Users can create price books"
    ON price_books FOR INSERT
    WITH CHECK (organization_id = auth.user_organization_id());

-- Users can update price books in their organization
CREATE POLICY "Users can update organization price books"
    ON price_books FOR UPDATE
    USING (organization_id = auth.user_organization_id())
    WITH CHECK (organization_id = auth.user_organization_id());

-- Users can delete price books in their organization
CREATE POLICY "Users can delete organization price books"
    ON price_books FOR DELETE
    USING (organization_id = auth.user_organization_id());

-- PRICE ITEMS TABLE POLICIES
-- Users can view price items from their organization's price books
CREATE POLICY "Users can view organization price items"
    ON price_items FOR SELECT
    USING (price_book_id IN (
        SELECT id FROM price_books 
        WHERE organization_id = auth.user_organization_id()
    ));

-- Users can manage price items in their organization's price books
CREATE POLICY "Users can manage organization price items"
    ON price_items FOR ALL
    USING (price_book_id IN (
        SELECT id FROM price_books 
        WHERE organization_id = auth.user_organization_id()
    ))
    WITH CHECK (price_book_id IN (
        SELECT id FROM price_books 
        WHERE organization_id = auth.user_organization_id()
    ));

-- PROCESSED POS TABLE POLICIES
-- Users can view processed POs from their organization
CREATE POLICY "Users can view organization processed POs"
    ON processed_pos FOR SELECT
    USING (organization_id = auth.user_organization_id());

-- Users can create processed POs in their organization
CREATE POLICY "Users can create processed POs"
    ON processed_pos FOR INSERT
    WITH CHECK (
        organization_id = auth.user_organization_id() AND
        validate_organization_po_limit(auth.user_organization_id())
    );

-- Users can update processed POs in their organization
CREATE POLICY "Users can update organization processed POs"
    ON processed_pos FOR UPDATE
    USING (organization_id = auth.user_organization_id())
    WITH CHECK (organization_id = auth.user_organization_id());

-- Users can delete processed POs in their organization
CREATE POLICY "Users can delete organization processed POs"
    ON processed_pos FOR DELETE
    USING (organization_id = auth.user_organization_id());

-- PO LINE ITEMS TABLE POLICIES
-- Users can view line items from their organization's processed POs
CREATE POLICY "Users can view organization PO line items"
    ON po_line_items FOR SELECT
    USING (processed_po_id IN (
        SELECT id FROM processed_pos 
        WHERE organization_id = auth.user_organization_id()
    ));

-- Users can manage line items in their organization's processed POs
CREATE POLICY "Users can manage organization PO line items"
    ON po_line_items FOR ALL
    USING (processed_po_id IN (
        SELECT id FROM processed_pos 
        WHERE organization_id = auth.user_organization_id()
    ))
    WITH CHECK (processed_po_id IN (
        SELECT id FROM processed_pos 
        WHERE organization_id = auth.user_organization_id()
    ));

-- Create trigger to increment PO count when processing POs
CREATE OR REPLACE FUNCTION increment_po_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment the monthly PO count for the organization
    UPDATE organizations 
    SET monthly_po_count = monthly_po_count + 1
    WHERE id = NEW.organization_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER increment_organization_po_count
    AFTER INSERT ON processed_pos
    FOR EACH ROW
    EXECUTE FUNCTION increment_po_count();

-- Create function to check organization limits before PO processing
CREATE OR REPLACE FUNCTION check_po_limit_before_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT validate_organization_po_limit(NEW.organization_id) THEN
        RAISE EXCEPTION 'Monthly PO limit exceeded for organization. Please upgrade your plan.';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_po_limit
    BEFORE INSERT ON processed_pos
    FOR EACH ROW
    EXECUTE FUNCTION check_po_limit_before_insert();

-- Grant necessary permissions for authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION auth.user_organization_id() TO authenticated;
GRANT EXECUTE ON FUNCTION auth.is_user_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION validate_organization_po_limit(UUID) TO authenticated; 