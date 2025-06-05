# Phase 4: Multi-Tenancy Implementation

## Overview
Implement true multi-tenancy with organization-based data isolation, user roles, and team management features.

## Multi-Tenancy Architecture

### Key Concepts
1. **Organization**: Top-level tenant (company/business)
2. **Users**: Belong to organizations with specific roles
3. **Data Isolation**: RLS ensures complete data separation
4. **Subscription Management**: Per-organization billing

## Database Schema Updates

### Step 1: Organization Features

```sql
-- Add organization settings table
CREATE TABLE organization_settings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    
    -- Branding
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#3B82F6',
    
    -- Features/Limits based on plan
    max_users INTEGER DEFAULT 5,
    max_price_books INTEGER DEFAULT 3,
    max_monthly_po_processing INTEGER DEFAULT 100,
    
    -- Preferences
    default_currency VARCHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Notifications
    notification_email VARCHAR(255),
    webhook_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add invitations table for team management
CREATE TABLE invitations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    invited_by UUID REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(organization_id, email)
);

-- Add activity log for audit trail
CREATE TABLE activity_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_org_email ON invitations(organization_id, email);
CREATE INDEX idx_activity_logs_org ON activity_logs(organization_id, created_at DESC);
```

### Step 2: RLS Policies for New Tables

```sql
-- Organization settings policies
ALTER TABLE organization_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their organization settings"
    ON organization_settings FOR SELECT
    USING (organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "Admins can update organization settings"
    ON organization_settings FOR UPDATE
    USING (
        organization_id IN (
            SELECT organization_id FROM users 
            WHERE id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- Invitations policies
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their organization invitations"
    ON invitations FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM users WHERE id = auth.uid()
        )
    );

CREATE POLICY "Admins can create invitations"
    ON invitations FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM users 
            WHERE id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- Activity logs policies
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their organization activity"
    ON activity_logs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM users WHERE id = auth.uid()
        )
    );
```

## Implementation Steps

### Step 1: Organization Management Service

1. **Create services/organization_service.py**
   ```python
   from typing import Optional, List, Dict
   from uuid import UUID, uuid4
   from datetime import datetime, timedelta
   from repositories.organization_repository import OrganizationRepository
   from repositories.user_repository import UserRepository
   from repositories.invitation_repository import InvitationRepository
   from utils.email_service import send_invitation_email
   import secrets
   
   class OrganizationService:
       def __init__(self):
           self.org_repo = OrganizationRepository()
           self.user_repo = UserRepository()
           self.invitation_repo = InvitationRepository()
       
       def create_organization(self, name: str, owner_user_id: UUID) -> Dict:
           """Create new organization with owner"""
           try:
               # Create organization
               org = self.org_repo.create({
                   'name': name,
                   'slug': self._generate_slug(name)
               })
               
               # Update user with organization and owner role
               self.user_repo.update(owner_user_id, {
                   'organization_id': org['id'],
                   'role': 'owner'
               })
               
               # Create default settings
               self._create_default_settings(org['id'])
               
               # Log activity
               self._log_activity(
                   org['id'], 
                   owner_user_id, 
                   'organization.created',
                   metadata={'organization_name': name}
               )
               
               return org
           
           except Exception as e:
               raise Exception(f"Failed to create organization: {str(e)}")
       
       def invite_user(self, org_id: UUID, email: str, role: str, invited_by: UUID) -> Dict:
           """Invite user to organization"""
           # Check if user already in organization
           existing_user = self.user_repo.get_by_email_and_org(email, org_id)
           if existing_user:
               raise ValueError("User already in organization")
           
           # Check invitation limits
           if not self._check_user_limit(org_id):
               raise ValueError("Organization user limit reached")
           
           # Create invitation
           token = secrets.token_urlsafe(32)
           expires_at = datetime.utcnow() + timedelta(days=7)
           
           invitation = self.invitation_repo.create({
               'organization_id': org_id,
               'email': email,
               'role': role,
               'invited_by': invited_by,
               'token': token,
               'expires_at': expires_at
           })
           
           # Send invitation email
           org = self.org_repo.get_by_id(org_id)
           send_invitation_email(email, org['name'], token)
           
           # Log activity
           self._log_activity(
               org_id,
               invited_by,
               'user.invited',
               metadata={'email': email, 'role': role}
           )
           
           return invitation
       
       def accept_invitation(self, token: str, user_id: UUID) -> Dict:
           """Accept invitation and join organization"""
           invitation = self.invitation_repo.get_by_token(token)
           
           if not invitation:
               raise ValueError("Invalid invitation")
           
           if invitation['accepted_at']:
               raise ValueError("Invitation already accepted")
           
           if datetime.utcnow() > invitation['expires_at']:
               raise ValueError("Invitation expired")
           
           # Update user organization and role
           self.user_repo.update(user_id, {
               'organization_id': invitation['organization_id'],
               'role': invitation['role']
           })
           
           # Mark invitation as accepted
           self.invitation_repo.update(invitation['id'], {
               'accepted_at': datetime.utcnow()
           })
           
           # Log activity
           self._log_activity(
               invitation['organization_id'],
               user_id,
               'invitation.accepted',
               metadata={'invited_by': invitation['invited_by']}
           )
           
           return {
               'organization_id': invitation['organization_id'],
               'role': invitation['role']
           }
       
       def update_user_role(self, org_id: UUID, user_id: UUID, new_role: str, updated_by: UUID):
           """Update user role in organization"""
           # Check permissions
           updater = self.user_repo.get_by_id(updated_by)
           if updater['role'] not in ['owner', 'admin']:
               raise ValueError("Insufficient permissions")
           
           # Prevent removing last owner
           if new_role != 'owner':
               owners = self.user_repo.get_owners_count(org_id)
               current_user = self.user_repo.get_by_id(user_id)
               if current_user['role'] == 'owner' and owners <= 1:
                   raise ValueError("Cannot remove last owner")
           
           # Update role
           self.user_repo.update(user_id, {'role': new_role})
           
           # Log activity
           self._log_activity(
               org_id,
               updated_by,
               'user.role_updated',
               metadata={
                   'user_id': str(user_id),
                   'new_role': new_role
               }
           )
       
       def remove_user(self, org_id: UUID, user_id: UUID, removed_by: UUID):
           """Remove user from organization"""
           # Check permissions
           remover = self.user_repo.get_by_id(removed_by)
           if remover['role'] not in ['owner', 'admin']:
               raise ValueError("Insufficient permissions")
           
           # Prevent removing last owner
           user = self.user_repo.get_by_id(user_id)
           if user['role'] == 'owner':
               owners = self.user_repo.get_owners_count(org_id)
               if owners <= 1:
                   raise ValueError("Cannot remove last owner")
           
           # Remove user from organization
           self.user_repo.update(user_id, {
               'organization_id': None,
               'role': 'member'
           })
           
           # Log activity
           self._log_activity(
               org_id,
               removed_by,
               'user.removed',
               metadata={'user_id': str(user_id)}
           )
       
       def _generate_slug(self, name: str) -> str:
           """Generate unique slug for organization"""
           base_slug = name.lower().replace(' ', '-')
           slug = base_slug
           counter = 1
           
           while self.org_repo.slug_exists(slug):
               slug = f"{base_slug}-{counter}"
               counter += 1
           
           return slug
       
       def _check_user_limit(self, org_id: UUID) -> bool:
           """Check if organization can add more users"""
           settings = self.org_repo.get_settings(org_id)
           current_users = self.user_repo.count_by_organization(org_id)
           return current_users < settings['max_users']
       
       def _create_default_settings(self, org_id: UUID):
           """Create default organization settings"""
           # Implementation for creating default settings
           pass
       
       def _log_activity(self, org_id: UUID, user_id: UUID, action: str, metadata: Dict = None):
           """Log activity for audit trail"""
           # Implementation for activity logging
           pass
   ```

### Step 2: Organization API Routes

1. **Create routes/organization_routes.py**
   ```python
   from flask import Blueprint, request, jsonify, g
   from utils.auth_decorators import login_required, organization_required
   from services.organization_service import OrganizationService
   from repositories.organization_repository import OrganizationRepository
   
   org_bp = Blueprint('organization', __name__)
   org_service = OrganizationService()
   org_repo = OrganizationRepository()
   
   @org_bp.route('/api/organization', methods=['GET'])
   @login_required
   @organization_required
   def get_organization():
       """Get current organization details"""
       org = org_repo.get_by_id(g.organization_id)
       settings = org_repo.get_settings(g.organization_id)
       
       return jsonify({
           'organization': org,
           'settings': settings
       })
   
   @org_bp.route('/api/organization/settings', methods=['PUT'])
   @login_required
   @organization_required
   def update_settings():
       """Update organization settings"""
       if g.user.role not in ['owner', 'admin']:
           return jsonify({'error': 'Insufficient permissions'}), 403
       
       data = request.get_json()
       allowed_fields = ['logo_url', 'primary_color', 'timezone', 
                         'notification_email', 'webhook_url']
       
       update_data = {k: v for k, v in data.items() if k in allowed_fields}
       
       settings = org_repo.update_settings(g.organization_id, update_data)
       
       return jsonify({'settings': settings})
   
   @org_bp.route('/api/organization/users', methods=['GET'])
   @login_required
   @organization_required
   def list_users():
       """List organization users"""
       users = org_repo.get_users(g.organization_id)
       return jsonify({'users': users})
   
   @org_bp.route('/api/organization/users/invite', methods=['POST'])
   @login_required
   @organization_required
   def invite_user():
       """Invite user to organization"""
       if g.user.role not in ['owner', 'admin']:
           return jsonify({'error': 'Insufficient permissions'}), 403
       
       data = request.get_json()
       email = data.get('email')
       role = data.get('role', 'member')
       
       try:
           invitation = org_service.invite_user(
               g.organization_id,
               email,
               role,
               g.user.id
           )
           return jsonify({'success': True, 'invitation': invitation})
       except ValueError as e:
           return jsonify({'error': str(e)}), 400
   
   @org_bp.route('/api/organization/users/<user_id>/role', methods=['PUT'])
   @login_required
   @organization_required
   def update_user_role(user_id):
       """Update user role"""
       if g.user.role not in ['owner', 'admin']:
           return jsonify({'error': 'Insufficient permissions'}), 403
       
       data = request.get_json()
       new_role = data.get('role')
       
       try:
           org_service.update_user_role(
               g.organization_id,
               user_id,
               new_role,
               g.user.id
           )
           return jsonify({'success': True})
       except ValueError as e:
           return jsonify({'error': str(e)}), 400
   
   @org_bp.route('/api/organization/users/<user_id>', methods=['DELETE'])
   @login_required
   @organization_required
   def remove_user(user_id):
       """Remove user from organization"""
       if g.user.role not in ['owner', 'admin']:
           return jsonify({'error': 'Insufficient permissions'}), 403
       
       try:
           org_service.remove_user(
               g.organization_id,
               user_id,
               g.user.id
           )
           return jsonify({'success': True})
       except ValueError as e:
           return jsonify({'error': str(e)}), 400
   
   @org_bp.route('/api/invitations/accept/<token>', methods=['POST'])
   @login_required
   def accept_invitation(token):
       """Accept invitation to join organization"""
       try:
           result = org_service.accept_invitation(token, g.user.id)
           return jsonify({
               'success': True,
               'organization_id': result['organization_id'],
               'role': result['role']
           })
       except ValueError as e:
           return jsonify({'error': str(e)}), 400
   ```

### Step 3: Organization Context Middleware

1. **Create middleware/organization_context.py**
   ```python
   from flask import g, request, session
   from utils.db_adapter import db_adapter, DatabaseMode
   from repositories.user_repository import UserRepository
   from repositories.organization_repository import OrganizationRepository
   
   class OrganizationContext:
       def __init__(self, app=None):
           self.app = app
           if app:
               self.init_app(app)
       
       def init_app(self, app):
           app.before_request(self.load_organization_context)
       
       def load_organization_context(self):
           """Load organization context for authenticated requests"""
           if hasattr(g, 'user') and g.user:
               if db_adapter.mode == DatabaseMode.SUPABASE:
                   user_repo = UserRepository()
                   user_data = user_repo.get_by_id(g.user.id)
                   
                   if user_data and user_data.get('organization_id'):
                       g.organization_id = user_data['organization_id']
                       
                       # Load organization details
                       org_repo = OrganizationRepository()
                       g.organization = org_repo.get_by_id(g.organization_id)
                       
                       # Check subscription status
                       if g.organization['subscription_status'] == 'suspended':
                           # Handle suspended accounts
                           pass
   ```

### Step 4: Update UI for Multi-Tenancy

1. **Create templates/organization/team.html**
   ```html
   {% extends "base.html" %}
   {% block content %}
   <div class="team-management">
       <h2>Team Management</h2>
       
       <div class="team-stats">
           <div class="stat-card">
               <h3>Team Members</h3>
               <p class="stat-number">{{ users|length }}</p>
               <p class="stat-limit">of {{ settings.max_users }} allowed</p>
           </div>
       </div>
       
       {% if g.user.role in ['owner', 'admin'] %}
       <div class="invite-section">
           <h3>Invite Team Member</h3>
           <form id="invite-form">
               <input type="email" name="email" placeholder="Email address" required>
               <select name="role">
                   <option value="member">Member</option>
                   <option value="admin">Admin</option>
                   {% if g.user.role == 'owner' %}
                   <option value="owner">Owner</option>
                   {% endif %}
               </select>
               <button type="submit">Send Invitation</button>
           </form>
       </div>
       {% endif %}
       
       <div class="team-list">
           <h3>Current Team</h3>
           <table>
               <thead>
                   <tr>
                       <th>Name</th>
                       <th>Email</th>
                       <th>Role</th>
                       <th>Joined</th>
                       {% if g.user.role in ['owner', 'admin'] %}
                       <th>Actions</th>
                       {% endif %}
                   </tr>
               </thead>
               <tbody>
                   {% for user in users %}
                   <tr>
                       <td>{{ user.username }}</td>
                       <td>{{ user.email }}</td>
                       <td>
                           {% if g.user.role in ['owner', 'admin'] and user.id != g.user.id %}
                           <select class="role-select" data-user-id="{{ user.id }}">
                               <option value="member" {% if user.role == 'member' %}selected{% endif %}>Member</option>
                               <option value="admin" {% if user.role == 'admin' %}selected{% endif %}>Admin</option>
                               {% if g.user.role == 'owner' %}
                               <option value="owner" {% if user.role == 'owner' %}selected{% endif %}>Owner</option>
                               {% endif %}
                           </select>
                           {% else %}
                           {{ user.role|title }}
                           {% endif %}
                       </td>
                       <td>{{ user.created_at|date }}</td>
                       {% if g.user.role in ['owner', 'admin'] %}
                       <td>
                           {% if user.id != g.user.id %}
                           <button class="remove-user" data-user-id="{{ user.id }}">Remove</button>
                           {% endif %}
                       </td>
                       {% endif %}
                   </tr>
                   {% endfor %}
               </tbody>
           </table>
       </div>
   </div>
   
   <script src="{{ url_for('static', filename='js/team-management.js') }}"></script>
   {% endblock %}
   ```

## Testing Multi-Tenancy

1. **Test data isolation**
   - Create multiple organizations
   - Verify users can't see other org data
   - Test RLS policies

2. **Test team management**
   - Invite users
   - Change roles
   - Remove users

3. **Test limits**
   - User limits
   - Feature limits
   - Plan restrictions

## Security Considerations

1. **Data Isolation**
   - RLS on all tables
   - Organization context validation
   - API permission checks

2. **Role-Based Access**
   - Owner: Full control
   - Admin: Team and settings management
   - Member: Basic access

3. **Audit Trail**
   - Log all sensitive actions
   - Track permission changes
   - Monitor access patterns

## Next Phase
Proceed to Phase 5: Stripe Integration
