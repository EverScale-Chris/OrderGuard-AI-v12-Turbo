# MCP Servers Setup Guide for OrderGuard AI

## Overview

Model Context Protocol (MCP) servers allow Cursor to directly interact with external services like Supabase, databases, and file systems. This dramatically accelerates development by letting AI assistants perform complex tasks on your behalf.

## Configured MCP Servers

### 1. Supabase MCP Server
**Purpose**: Direct integration with Supabase cloud platform
**When to use**: Production database management, schema design, deployment tasks

**Available Tools** (20+ tools):
- `create_project` - Spin up new Supabase projects
- `list_projects` - View all your projects
- `get_project_config` - Fetch project URLs, keys, and settings
- `list_tables` - Explore database schema
- `execute_sql` - Run SQL queries and reports
- `create_migration` - Design and track schema changes
- `generate_types` - Create TypeScript types from schema
- `get_logs` - Debug issues with project logs
- `pause_project` / `restore_project` - Manage project lifecycle
- `create_branch` - Create development database branches
- `list_branches` - Manage database branches

### 2. Postgres Local MCP Server
**Purpose**: Query local Supabase development database
**When to use**: Local development, testing queries, exploring data

**Available Tools**:
- `list_schemas` - Show all database schemas
- `list_tables` - List tables in schemas
- `describe_table` - Get table structure and constraints
- `query` - Execute read-only SQL queries
- `list_columns` - Show column details

### 3. Filesystem MCP Server
**Purpose**: File and directory operations
**When to use**: Code generation, file management, project structure tasks

**Available Tools**:
- `read_file` - Read file contents
- `write_file` - Create or update files
- `list_directory` - Browse directory contents
- `create_directory` - Create new directories
- `move_file` - Rename or move files
- `delete_file` - Remove files

## Common Use Cases for OrderGuard Development

### Database Migration Tasks
```
Ask Cursor: "Help me migrate the users table from SQLAlchemy to Supabase with RLS policies"

What happens:
1. Cursor uses Supabase MCP to examine current schema
2. Creates migration files for the new structure
3. Generates RLS policies for multi-tenancy
4. Updates TypeScript types
5. Creates test queries to verify migration
```

### AI Feature Development
```
Ask Cursor: "Set up automatic embeddings for price_items table"

What happens:
1. Uses Supabase MCP to check if pgvector is enabled
2. Creates migration to add embedding column
3. Sets up embedding triggers and functions
4. Generates Edge Function for embedding processing
5. Creates TypeScript types for the new schema
```

### Schema Design and Optimization
```
Ask Cursor: "Optimize the database schema for multi-tenant performance"

What happens:
1. Analyzes current schema using list_tables and describe_table
2. Suggests RLS policy improvements
3. Recommends indexing strategies
4. Creates performance test queries
5. Generates migration files for optimizations
```

### Local Development and Testing
```
Ask Cursor: "Show me all price items with mismatched prices in local database"

What happens:
1. Uses Postgres Local MCP to query development data
2. Generates complex analytical queries
3. Formats results for easy review
4. Suggests data cleanup strategies
```

## How to Use MCP Servers

### 1. Natural Language Commands
Simply ask Cursor to perform tasks using natural language:

- "Create a new table for organizations with RLS policies"
- "Generate TypeScript types for all my Supabase tables"
- "Show me the logs for my Edge Function deployments"
- "Create a database branch for testing AI features"
- "Run a query to find all POs processed this month"

### 2. Specific Development Workflows

#### Setting Up New Features
```
Prompt: "I want to add semantic search to OrderGuard. Set up the database schema and Edge Functions."

Expected Actions:
1. Check if pgvector extension is enabled
2. Create migration for embedding columns
3. Set up automatic embedding triggers
4. Create Edge Function for embedding generation
5. Generate TypeScript types
6. Create example queries for semantic search
```

#### Database Performance Optimization
```
Prompt: "Analyze and optimize the database performance for the price_items table"

Expected Actions:
1. Query current table structure and indexes
2. Analyze query patterns from logs
3. Suggest and create optimal indexes
4. Generate RLS policy improvements
5. Create performance test queries
```

#### Migration Verification
```
Prompt: "Verify that all data migrated correctly from the old system"

Expected Actions:
1. Query both old and new data sources
2. Compare record counts and structures
3. Identify any data discrepancies
4. Generate validation reports
5. Suggest data cleanup scripts
```

## Best Practices

### 1. Start with Schema Exploration
Before making changes, ask Cursor to explore your current schema:
```
"Show me the current database schema and explain the relationships"
```

### 2. Use Branches for Experimentation
Create database branches for testing:
```
"Create a database branch called 'ai-features' for testing embedding functionality"
```

### 3. Generate Types After Schema Changes
Always update TypeScript types after database changes:
```
"Generate updated TypeScript types after this migration"
```

### 4. Test Locally First
Use the local Postgres MCP for development:
```
"Test this query on my local database before running on production"
```

### 5. Monitor Performance
Regularly check logs and performance:
```
"Show me any errors or performance issues from the last 24 hours"
```

## Troubleshooting

### MCP Server Not Responding
1. Restart Cursor
2. Check that npm packages are installed
3. Verify access tokens are correct
4. Check network connectivity

### Local Database Connection Issues
1. Ensure Supabase is running locally: `supabase status`
2. Verify the connection string in mcp.json
3. Check if local database is accessible: `psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres"`

### Permission Issues
1. Verify your Supabase personal access token has correct permissions
2. Check that your Supabase user has admin access to the project
3. Ensure RLS policies allow your operations

## Advanced Workflows

### Automated Database Design
```
Prompt: "Design a complete multi-tenant schema for OrderGuard with proper RLS policies, indexes, and relationships"
```

### AI-Powered Data Analysis
```
Prompt: "Analyze our PO processing data and suggest improvements to the matching algorithm"
```

### Automated Testing Setup
```
Prompt: "Create comprehensive tests for all database functions and RLS policies"
```

### Performance Monitoring
```
Prompt: "Set up monitoring queries to track database performance and usage patterns"
```

## Integration with OrderGuard Development

The MCP servers are specifically configured to accelerate your OrderGuard AI migration:

1. **Phase 1-2**: Use Supabase MCP for initial setup and schema migration
2. **Phase 3**: Leverage for authentication and user migration
3. **Phase 4**: Optimize multi-tenancy with RLS policy generation
4. **Phase 5**: Integrate with Stripe webhook handling
5. **Phase 6**: Set up AI features including embeddings and vector search
6. **Phase 7**: Deploy and monitor production systems

Remember: These MCP servers give Cursor superpowers for database and infrastructure management. Use them liberally to accelerate development and reduce manual tasks! 