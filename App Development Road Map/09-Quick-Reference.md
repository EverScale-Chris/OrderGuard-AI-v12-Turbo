# OrderGuard SaaS Migration Quick Reference

## 🚀 Common Commands

### Supabase CLI
```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Login to Supabase
supabase login

# Initialize project
supabase init

# Start local development
supabase start

# Link to remote project
supabase link --project-ref <project-id>

# Generate types
supabase gen types typescript --linked > types/supabase.ts

# Run migrations
supabase db push

# Pull remote schema
supabase db pull

# Deploy Edge Functions
supabase functions deploy embed

# View logs
supabase functions logs embed
```

### Stripe CLI
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Listen to webhooks locally
stripe listen --forward-to localhost:5000/stripe/webhook

# Trigger test events
stripe trigger payment_intent.succeeded

# Create test customer
stripe customers create --email="test@example.com"
```

### MCP Commands in Cursor
```bash
# Ask Cursor to use MCP servers with natural language:

# Database operations
"Show me the current schema of my Supabase project"
"Create a migration to add embedding columns to price_items"
"Generate TypeScript types for all my tables"
"Create a database branch for testing AI features"

# Development tasks
"Set up automatic embeddings for the price_items table"
"Optimize RLS policies for better performance"
"Create Edge Function for embedding generation"
"Analyze query performance and suggest indexes"

# Data analysis
"Show me all POs processed this month"
"Find price mismatches in the local database"
"Generate a report of user activity"
"Identify potential data quality issues"
```

## 📝 Essential Code Snippets

### Supabase Client Setup with AI
```python
# utils/supabase_client.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    return create_client(url, key)

def get_supabase_admin_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    return create_client(url, key)
```

### MCP Configuration
```json
// .cursor/mcp.json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "<your-personal-access-token>"
      ]
    },
    "postgres-local": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
      ]
    }
  }
}
```

### AI Extensions Setup
```sql
-- Enable AI-related extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pgmq;

-- Create embedding jobs queue
SELECT pgmq.create('embedding_jobs');

-- Schedule embedding processing
SELECT cron.schedule(
    'process-embeddings',
    '10 seconds',
    $$SELECT util.process_embeddings();$$
);
```

### Automatic Embeddings Setup
```sql
-- Create embedding trigger function
CREATE OR REPLACE FUNCTION util.queue_embeddings()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  content_function text = TG_ARGV[0];
  embedding_column text = TG_ARGV[1];
BEGIN
  PERFORM pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', NEW.id,
      'schema', TG_TABLE_SCHEMA,
      'table', TG_TABLE_NAME,
      'contentFunction', content_function,
      'embeddingColumn', embedding_column
    )
  );
  RETURN NEW;
END;
$$;

-- Add to your table
CREATE TRIGGER embed_on_insert
  AFTER INSERT ON your_table
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('content_function', 'embedding');
```

### Vector Search Implementation
```python
# Semantic search with pgvector
def semantic_search(query: str, limit: int = 10):
    # Generate embedding for query
    embedding = openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    
    # Perform vector search
    results = supabase.rpc(
        'match_documents',
        {
            'query_embedding': embedding,
            'match_threshold': 0.7,
            'match_count': limit
        }
    ).execute()
    
    return results.data
```

### RLS Policy Templates with Performance
```sql
-- Optimized RLS policy with index usage
CREATE POLICY "Users can view org data"
ON table_name FOR SELECT
TO authenticated
USING (
    organization_id IN (
        SELECT organization_id FROM users
        WHERE id = auth.uid()
    )
);

-- Create supporting index
CREATE INDEX idx_users_auth_org ON users(id, organization_id);

-- Policy with custom claims (2025 feature)
CREATE POLICY "Admins can do everything"
ON table_name FOR ALL
TO authenticated
USING (
    (auth.jwt() -> 'user_metadata' ->> 'role')::text = 'admin'
);
```

### Auth Hooks for Custom Claims
```sql
-- Create auth hook for custom claims
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  claims jsonb;
  user_role text;
BEGIN
  -- Get user role
  SELECT role INTO user_role 
  FROM public.user_roles 
  WHERE user_id = (event->>'user_id')::uuid;
  
  claims := event->'claims';
  
  IF user_role IS NOT NULL THEN
    claims := jsonb_set(claims, '{user_role}', to_jsonb(user_role));
  END IF;
  
  event := jsonb_set(event, '{claims}', claims);
  RETURN event;
END;
$$;
```

### Edge Function for Embeddings
```typescript
// supabase/functions/embed/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import OpenAI from 'https://deno.land/x/openai@v4.20.1/mod.ts'

const openai = new OpenAI({
  apiKey: Deno.env.get('OPENAI_API_KEY'),
})

serve(async (req) => {
  const { text } = await req.json()
  
  // Generate embedding
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  })
  
  return new Response(
    JSON.stringify({ embedding: response.data[0].embedding }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

### Hybrid Search Query
```sql
-- Combine semantic and keyword search
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  similarity FLOAT,
  rank FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH semantic AS (
    SELECT 
      id,
      content,
      1 - (embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding
    LIMIT match_count
  ),
  keyword AS (
    SELECT 
      id,
      content,
      ts_rank(to_tsvector('english', content), 
              plainto_tsquery('english', query_text)) AS rank
    FROM documents
    WHERE to_tsvector('english', content) @@ 
          plainto_tsquery('english', query_text)
    ORDER BY rank DESC
    LIMIT match_count
  )
  SELECT DISTINCT ON (COALESCE(s.id, k.id))
    COALESCE(s.id, k.id) AS id,
    COALESCE(s.content, k.content) AS content,
    COALESCE(s.similarity, 0) AS similarity,
    COALESCE(k.rank, 0) AS rank
  FROM semantic s
  FULL OUTER JOIN keyword k ON s.id = k.id
  ORDER BY COALESCE(s.id, k.id), 
           (COALESCE(s.similarity, 0) + COALESCE(k.rank, 0)) DESC;
END;
$$;
```

## 🔐 Security Checklist

### Environment Variables
```bash
# Required for production with AI
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx  # Never expose to client!
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
SESSION_SECRET=<32+ character random string>
SENDGRID_API_KEY=xxx
REDIS_URL=redis://xxx
APP_URL=https://orderguard.com
OPENAI_API_KEY=sk-xxx  # For AI features
```

### RLS Performance Checks
```sql
-- Check RLS performance impact
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM your_table 
WHERE organization_id = 'xxx';

-- Ensure indexes are used
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## 🤖 MCP Server Usage Patterns

### Schema Management with MCP
```bash
# Use Cursor with MCP to manage schema
"Analyze my current database schema and suggest improvements"
"Create a migration to add vector columns for AI features"
"Generate optimized RLS policies for multi-tenant access"
"Set up indexes for better query performance"
```

### AI Feature Development with MCP
```bash
# Let Cursor handle AI infrastructure
"Set up automatic embeddings for all text content"
"Create semantic search functionality for price items"
"Build AI-powered analytics with insights generation"
"Implement anomaly detection for price mismatches"
```

### Development Workflow with MCP
```bash
# Database branching for safe development
"Create a database branch for testing new features"
"Compare schema between branches"
"Merge changes from development branch to main"

# Type generation and code updates
"Generate TypeScript types after schema changes"
"Update all API endpoints to use new schema"
"Create test data for the new features"
```

## 🛠️ Common Issues & Solutions

### Issue: Slow vector search
```sql
-- Solution: Use appropriate index and limit dimensions
CREATE INDEX ON items 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Pre-filter before vector search
WITH filtered AS (
  SELECT * FROM items 
  WHERE category = 'electronics'
  AND price < 1000
)
SELECT * FROM filtered
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

### Issue: Embedding generation timeout
```typescript
// Solution: Increase timeout and batch process
const BATCH_SIZE = 10;
const TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

async function processBatch(jobs) {
  const embeddings = await Promise.all(
    jobs.map(job => generateEmbedding(job.text))
  );
  // Update database in batch
}
```

### Issue: RLS policies blocking AI operations
```sql
-- Solution: Use security definer functions
CREATE OR REPLACE FUNCTION generate_embedding_secure(
  table_name TEXT,
  row_id UUID,
  content TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Function runs with owner privileges
  -- bypassing RLS for system operations
  PERFORM util.queue_embeddings(table_name, row_id, content);
END;
$$;
```

### Issue: MCP Server Not Responding
```bash
# Troubleshooting steps
1. Restart Cursor
2. Check .cursor/mcp.json configuration
3. Verify Supabase personal access token
4. Test with: "Show me my Supabase projects"
5. Check local Supabase is running: supabase status
```

## 📊 AI Monitoring Queries

### Check embedding generation status
```sql
-- View pending embedding jobs
SELECT 
  msg_id,
  read_ct,
  enqueued_at,
  message->>'table' as table_name,
  message->>'id' as row_id
FROM pgmq.q_embedding_jobs
WHERE vt > NOW()
ORDER BY enqueued_at DESC;

-- Check embedding coverage
SELECT 
  COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embeddings,
  COUNT(*) FILTER (WHERE embedding IS NULL) as without_embeddings,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / COUNT(*), 2) as percentage
FROM your_table;
```

### AI usage tracking
```sql
-- Track AI API calls
CREATE TABLE ai_usage_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  operation TEXT,
  model TEXT,
  tokens_used INTEGER,
  cost_usd DECIMAL(10, 4),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Daily AI costs
SELECT 
  DATE(created_at) as date,
  operation,
  SUM(tokens_used) as total_tokens,
  SUM(cost_usd) as total_cost
FROM ai_usage_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), operation
ORDER BY date DESC;
```

## 🚨 Emergency Procedures

### Disable AI features
```sql
-- Temporarily disable embedding generation
SELECT cron.unschedule('process-embeddings');

-- Clear embedding queue
SELECT pgmq.purge_queue('embedding_jobs');

-- Disable AI features flag
UPDATE app_settings 
SET value = 'false' 
WHERE key = 'ai_features_enabled';
```

### Fix broken embeddings
```sql
-- Identify corrupted embeddings
SELECT id, model_number
FROM price_items
WHERE embedding IS NOT NULL
AND array_length(embedding::real[], 1) != 1536;

-- Reset and regenerate
UPDATE price_items
SET embedding = NULL
WHERE array_length(embedding::real[], 1) != 1536;

-- Trigger regeneration
SELECT util.regenerate_embeddings('price_items');
```

## 📚 Useful Links

- [Supabase Dashboard](https://app.supabase.com)
- [Stripe Dashboard](https://dashboard.stripe.com)
- [Supabase AI Docs](https://supabase.com/docs/guides/ai)
- [Supabase MCP Server](https://supabase.com/blog/mcp-server)
- [MCP Documentation](https://supabase.com/docs/guides/getting-started/mcp)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Platform](https://platform.openai.com)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Stripe Testing Cards](https://stripe.com/docs/testing#cards)

## 💡 Pro Tips for 2025

1. **Always use halfvec for embeddings** - Saves 50% storage with minimal accuracy loss
2. **Cache embeddings aggressively** - OpenAI charges per token
3. **Use hybrid search** - Combines best of semantic and keyword search
4. **Monitor RLS performance** - Use EXPLAIN ANALYZE regularly
5. **Batch AI operations** - Reduces API calls and costs
6. **Use Edge Functions for light AI** - Faster response times
7. **Enable pgvector indexes after data load** - Much faster initial import
8. **Leverage MCP servers in Cursor** - Let AI handle database and infrastructure tasks
9. **Create database branches for experimentation** - Safe testing environment
10. **Use natural language with MCP** - "Create a table with RLS" vs manual SQL

---

Remember: When in doubt, test in development first with `supabase start`! Use MCP servers to accelerate development through natural language commands. 