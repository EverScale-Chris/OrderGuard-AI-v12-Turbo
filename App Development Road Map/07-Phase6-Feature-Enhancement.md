# Phase 6: Feature Enhancement and Admin Dashboard

## Overview
Enhance the application with advanced features including AI-powered search, automatic embeddings, usage analytics, plan enforcement, admin dashboard, and improved user experience features.

## Prerequisites
- Phases 1-5 completed
- Stripe integration working
- Multi-tenant structure in place
- All data migrated to Supabase
- OpenAI API key configured

## Step-by-Step Implementation

### Step 1: AI-Powered Search with Automatic Embeddings

1. **Set up automatic embeddings infrastructure**
   ```sql
   -- Enable required extensions (if not already enabled)
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pg_net;
   CREATE EXTENSION IF NOT EXISTS pg_cron;
   CREATE EXTENSION IF NOT EXISTS pgmq;
   
   -- Create embedding jobs queue
   SELECT pgmq.create('embedding_jobs');
   
   -- Create utility schema
   CREATE SCHEMA IF NOT EXISTS util;
   
   -- Store project URL in Vault
   SELECT vault.create_secret('<your-project-url>', 'project_url');
   ```

2. **Create automatic embedding functions**
   ```sql
   -- Utility function to get project URL
   CREATE OR REPLACE FUNCTION util.project_url()
   RETURNS text
   LANGUAGE plpgsql
   SECURITY DEFINER
   AS $$
   DECLARE
     secret_value text;
   BEGIN
     SELECT decrypted_secret INTO secret_value 
     FROM vault.decrypted_secrets 
     WHERE name = 'project_url';
     RETURN secret_value;
   END;
   $$;
   
   -- Generic function to invoke Edge Functions
   CREATE OR REPLACE FUNCTION util.invoke_edge_function(
     name text,
     body jsonb,
     timeout_milliseconds int = 5 * 60 * 1000
   )
   RETURNS void
   LANGUAGE plpgsql
   AS $$
   DECLARE
     headers_raw text;
     auth_header text;
   BEGIN
     headers_raw := current_setting('request.headers', true);
     auth_header := CASE
       WHEN headers_raw IS NOT NULL THEN
         (headers_raw::json->>'authorization')
       ELSE NULL
     END;
     
     PERFORM net.http_post(
       url => util.project_url() || '/functions/v1/' || name,
       headers => jsonb_build_object(
         'Content-Type', 'application/json',
         'Authorization', auth_header
       ),
       body => body,
       timeout_milliseconds => timeout_milliseconds
     );
   END;
   $$;
   
   -- Trigger function to queue embedding jobs
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
   
   -- Process embedding jobs
   CREATE OR REPLACE FUNCTION util.process_embeddings(
     batch_size int = 10,
     max_requests int = 10,
     timeout_milliseconds int = 5 * 60 * 1000
   )
   RETURNS void
   LANGUAGE plpgsql
   AS $$
   DECLARE
     job_batches jsonb[];
     batch jsonb;
   BEGIN
     WITH numbered_jobs AS (
       SELECT
         message || jsonb_build_object('jobId', msg_id) as job_info,
         (row_number() OVER (ORDER BY 1) - 1) / batch_size as batch_num
       FROM pgmq.read(
         queue_name => 'embedding_jobs',
         vt => timeout_milliseconds / 1000,
         qty => max_requests * batch_size
       )
     ),
     batched_jobs AS (
       SELECT
         jsonb_agg(job_info) as batch_array,
         batch_num
       FROM numbered_jobs
       GROUP BY batch_num
     )
     SELECT array_agg(batch_array)
     FROM batched_jobs
     INTO job_batches;
     
     FOREACH batch IN ARRAY job_batches LOOP
       PERFORM util.invoke_edge_function(
         name => 'embed',
         body => batch,
         timeout_milliseconds => timeout_milliseconds
       );
     END LOOP;
   END;
   $$;
   
   -- Schedule embedding processing
   SELECT cron.schedule(
     'process-embeddings',
     '10 seconds',
     $$SELECT util.process_embeddings();$$
   );
   ```

3. **Add embeddings to price books and POs**
   ```sql
   -- Add embedding columns
   ALTER TABLE price_items ADD COLUMN IF NOT EXISTS embedding halfvec(1536);
   ALTER TABLE po_line_items ADD COLUMN IF NOT EXISTS description_embedding halfvec(1536);
   
   -- Create indexes for vector search
   CREATE INDEX IF NOT EXISTS idx_price_items_embedding 
   ON price_items USING hnsw (embedding halfvec_cosine_ops);
   
   CREATE INDEX IF NOT EXISTS idx_po_line_items_embedding 
   ON po_line_items USING hnsw (description_embedding halfvec_cosine_ops);
   
   -- Embedding input function for price items
   CREATE OR REPLACE FUNCTION price_item_embedding_input(item price_items)
   RETURNS text
   LANGUAGE plpgsql
   IMMUTABLE
   AS $$
   BEGIN
     RETURN item.model_number || ' ' || COALESCE(item.description, '');
   END;
   $$;
   
   -- Add triggers for automatic embeddings
   CREATE TRIGGER embed_price_items_on_insert
     AFTER INSERT ON price_items
     FOR EACH ROW
     EXECUTE FUNCTION util.queue_embeddings('price_item_embedding_input', 'embedding');
   
   CREATE TRIGGER embed_price_items_on_update
     AFTER UPDATE OF model_number, description ON price_items
     FOR EACH ROW
     EXECUTE FUNCTION util.queue_embeddings('price_item_embedding_input', 'embedding');
   ```

4. **Create semantic search functions**
   ```python
   # utils/semantic_search.py
   import numpy as np
   from utils.supabase_client import get_supabase_client
   import openai
   
   class SemanticSearch:
       def __init__(self):
           self.supabase = get_supabase_client()
           self.openai_client = openai.Client()
       
       def generate_embedding(self, text: str):
           """Generate embedding for search query"""
           response = self.openai_client.embeddings.create(
               model="text-embedding-3-small",
               input=text
           )
           return response.data[0].embedding
       
       def search_price_items(self, query: str, price_book_id: str, limit: int = 10):
           """Semantic search for price items"""
           # Generate embedding for query
           query_embedding = self.generate_embedding(query)
           
           # Perform vector search
           result = self.supabase.rpc(
               'search_price_items',
               {
                   'query_embedding': query_embedding,
                   'price_book_id': price_book_id,
                   'match_threshold': 0.7,
                   'match_count': limit
               }
           ).execute()
           
           return result.data
       
       def hybrid_search(self, query: str, price_book_id: str):
           """Combine semantic and keyword search"""
           # Semantic search
           semantic_results = self.search_price_items(query, price_book_id)
           
           # Keyword search
           keyword_results = self.supabase.table('price_items').select(
               '*'
           ).eq(
               'price_book_id', price_book_id
           ).ilike(
               'model_number', f'%{query}%'
           ).limit(10).execute()
           
           # Combine and deduplicate results
           combined = self._merge_results(semantic_results, keyword_results.data)
           return combined
   ```

### Step 2: Usage Analytics with AI Insights

1. **Create analytics tables**
   ```sql
   -- Analytics summary table
   CREATE TABLE analytics_summary (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
       period_start DATE,
       period_end DATE,
       total_pos_processed INTEGER DEFAULT 0,
       total_matches INTEGER DEFAULT 0,
       total_mismatches INTEGER DEFAULT 0,
       total_not_found INTEGER DEFAULT 0,
       total_savings DECIMAL(10, 2) DEFAULT 0,
       avg_processing_time INTERVAL,
       ai_insights JSONB, -- Store AI-generated insights
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- Create indexes for performance
   CREATE INDEX idx_analytics_org_period ON analytics_summary(organization_id, period_start);
   
   -- User activity tracking
   CREATE TABLE user_activity (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       user_id UUID REFERENCES users(id) ON DELETE CASCADE,
       organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
       activity_type VARCHAR(100),
       activity_details JSONB,
       ip_address INET,
       user_agent TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- Search queries tracking for improving AI
   CREATE TABLE search_queries (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       user_id UUID REFERENCES users(id) ON DELETE CASCADE,
       query TEXT,
       query_embedding halfvec(1536),
       results_count INTEGER,
       clicked_result JSONB,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- RLS policies
   ALTER TABLE analytics_summary ENABLE ROW LEVEL SECURITY;
   ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
   ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY "Users can view their org analytics"
   ON analytics_summary FOR SELECT
   TO authenticated
   USING (
       organization_id IN (
           SELECT organization_id FROM users
           WHERE id = auth.uid()
       )
   );
   ```

2. **Create AI-powered analytics service**
   ```python
   # utils/ai_analytics.py
   from datetime import datetime, timedelta
   from utils.supabase_client import get_supabase_client
   import pandas as pd
   import openai
   
   class AIAnalyticsService:
       def __init__(self):
           self.supabase = get_supabase_client()
           self.openai_client = openai.Client()
       
       def generate_insights(self, analytics_data):
           """Generate AI insights from analytics data"""
           prompt = f"""
           Analyze this procurement data and provide actionable insights:
           - Total POs: {analytics_data['total_pos']}
           - Match rate: {analytics_data['match_rate']}%
           - Total savings: ${analytics_data['total_savings']}
           - Most common mismatches: {analytics_data['top_mismatches']}
           
           Provide 3-5 specific recommendations to improve procurement efficiency.
           """
           
           response = self.openai_client.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "You are a procurement analytics expert."},
                   {"role": "user", "content": prompt}
               ]
           )
           
           return response.choices[0].message.content
       
       def generate_monthly_summary(self, organization_id):
           """Generate monthly analytics with AI insights"""
           # ... existing analytics code ...
           
           # Generate AI insights
           insights = self.generate_insights(analytics_data)
           
           # Save with AI insights
           self.supabase.table('analytics_summary').upsert({
               'organization_id': organization_id,
               'period_start': start_of_month.date().isoformat(),
               'period_end': now.date().isoformat(),
               'total_pos_processed': total_pos,
               'total_matches': total_matches,
               'total_mismatches': total_mismatches,
               'total_not_found': total_not_found,
               'total_savings': total_savings,
               'ai_insights': {
                   'summary': insights,
                   'generated_at': datetime.now().isoformat()
               }
           }).execute()
   ```

### Step 3: Enhanced Admin Dashboard with AI Features

1. **Create super admin interface with AI capabilities**
   ```python
   # utils/admin_ai.py
   from utils.supabase_client import get_supabase_admin_client
   from datetime import datetime, timedelta
   import openai
   
   class AdminAIService:
       def __init__(self):
           self.supabase = get_supabase_admin_client()
           self.openai_client = openai.Client()
       
       def detect_anomalies(self):
           """Use AI to detect unusual patterns in usage"""
           # Get recent activity data
           recent_activity = self.supabase.table('user_activity').select(
               '*'
           ).gte(
               'created_at', 
               (datetime.now() - timedelta(hours=24)).isoformat()
           ).execute()
           
           # Analyze with AI
           prompt = f"""
           Analyze this user activity data for anomalies:
           {recent_activity.data}
           
           Look for:
           - Unusual usage patterns
           - Potential security issues
           - Performance problems
           """
           
           response = self.openai_client.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "You are a security analyst."},
                   {"role": "user", "content": prompt}
               ]
           )
           
           return response.choices[0].message.content
       
       def generate_platform_insights(self):
           """Generate AI insights for platform health"""
           metrics = self.get_platform_metrics()
           
           prompt = f"""
           Analyze these platform metrics:
           - Total organizations: {metrics['total_organizations']}
           - Active subscriptions: {metrics['active_subscriptions']}
           - MRR: ${metrics['mrr']}
           - Recent signups: {metrics['recent_signups']}
           
           Provide insights on:
           1. Growth trends
           2. Potential churn risks
           3. Recommendations for improvement
           """
           
           response = self.openai_client.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "You are a SaaS business analyst."},
                   {"role": "user", "content": prompt}
               ]
           )
           
           return response.choices[0].message.content
   ```

2. **Add AI-powered routes**
   ```python
   # Add to app.py
   from utils.admin_ai import AdminAIService
   from utils.semantic_search import SemanticSearch
   
   admin_ai_service = AdminAIService()
   semantic_search = SemanticSearch()
   
   @app.route('/api/search/semantic', methods=['POST'])
   @login_required
   def semantic_search_api():
       """AI-powered semantic search"""
       data = request.json
       query = data.get('query')
       price_book_id = data.get('price_book_id')
       
       if not query or not price_book_id:
           return jsonify({'error': 'Missing query or price_book_id'}), 400
       
       # Verify user has access to price book
       org = get_user_organization(current_user.id)
       price_book = supabase.table('price_books').select('*').eq(
           'id', price_book_id
       ).eq('organization_id', org['id']).single().execute()
       
       if not price_book.data:
           return jsonify({'error': 'Access denied'}), 403
       
       results = semantic_search.hybrid_search(query, price_book_id)
       
       # Track search query for improvements
       supabase.table('search_queries').insert({
           'user_id': current_user.id,
           'query': query,
           'results_count': len(results)
       }).execute()
       
       return jsonify({'results': results})
   
   @app.route('/api/analytics/insights')
   @login_required
   def get_ai_insights():
       """Get AI-generated insights for organization"""
       org = get_user_organization(current_user.id)
       
       # Get latest analytics with AI insights
       latest = supabase.table('analytics_summary').select('*').eq(
           'organization_id', org['id']
       ).order('created_at', desc=True).limit(1).execute()
       
       if latest.data and latest.data[0].get('ai_insights'):
           return jsonify(latest.data[0]['ai_insights'])
       
       # Generate new insights if none exist
       ai_analytics = AIAnalyticsService()
       ai_analytics.generate_monthly_summary(org['id'])
       
       return jsonify({'message': 'Insights generated, please refresh'})
   ```

### Step 4: Advanced Features

1. **Bulk PO processing with AI matching**
   ```python
   # utils/bulk_processor_ai.py
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   from utils.semantic_search import SemanticSearch
   
   class AIBulkProcessor:
       def __init__(self):
           self.executor = ThreadPoolExecutor(max_workers=4)
           self.semantic_search = SemanticSearch()
       
       async def process_bulk_pos_with_ai(self, files, price_book_id, organization_id):
           """Process multiple POs with AI-enhanced matching"""
           tasks = []
           results = []
           
           for file in files:
               task = self.executor.submit(
                   self.process_single_po_with_ai,
                   file,
                   price_book_id,
                   organization_id
               )
               tasks.append(task)
           
           for task in tasks:
               result = await asyncio.wrap_future(task)
               results.append(result)
           
           return results
       
       def process_single_po_with_ai(self, file, price_book_id, organization_id):
           """Process PO with semantic matching for items not found"""
           # Extract data from PDF
           extracted_data = extract_data_from_pdf(file)
           
           # Try exact matching first
           comparison_results = compare_with_price_book(extracted_data, price_book_id)
           
           # For items not found, try semantic search
           for item in comparison_results['not_found']:
               semantic_matches = self.semantic_search.search_price_items(
                   item['description'], 
                   price_book_id, 
                   limit=3
               )
               
               if semantic_matches:
                   item['suggested_matches'] = semantic_matches
                   item['ai_confidence'] = semantic_matches[0]['similarity']
           
           return comparison_results
   ```

2. **AI-powered price anomaly detection**
   ```python
   # utils/price_anomaly.py
   class PriceAnomalyDetector:
       def __init__(self):
           self.supabase = get_supabase_client()
       
       def detect_price_anomalies(self, organization_id):
           """Detect unusual price changes using statistical analysis"""
           # Get recent price mismatches
           mismatches = self.supabase.table('po_line_items').select(
               'model_number, po_price, book_price, processed_po_id'
           ).eq('status', 'Mismatch').eq(
               'processed_pos.organization_id', organization_id
           ).execute()
           
           # Analyze patterns
           anomalies = []
           for item in mismatches.data:
               price_diff_pct = abs(item['po_price'] - item['book_price']) / item['book_price'] * 100
               
               if price_diff_pct > 20:  # More than 20% difference
                   anomalies.append({
                       'model_number': item['model_number'],
                       'price_difference': price_diff_pct,
                       'severity': 'high' if price_diff_pct > 50 else 'medium'
                   })
           
           return anomalies
   ```

### Step 5: Notification System with AI Alerts

1. **Create notification tables**
   ```sql
   CREATE TABLE notifications (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       user_id UUID REFERENCES users(id) ON DELETE CASCADE,
       type VARCHAR(50),
       title VARCHAR(255),
       message TEXT,
       data JSONB,
       ai_generated BOOLEAN DEFAULT FALSE,
       read BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE notification_preferences (
       id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
       user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
       ai_insights BOOLEAN DEFAULT TRUE,
       price_anomalies BOOLEAN DEFAULT TRUE,
       usage_alerts BOOLEAN DEFAULT TRUE,
       weekly_summary BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **AI-powered notification service**
   ```python
   # utils/ai_notifications.py
   class AINotificationService:
       def __init__(self):
           self.supabase = get_supabase_client()
           self.openai_client = openai.Client()
       
       def generate_weekly_summary(self, user_id, organization_id):
           """Generate AI-powered weekly summary"""
           # Get week's data
           week_data = self._get_weekly_data(organization_id)
           
           # Generate summary with AI
           prompt = f"""
           Create a brief, actionable weekly summary:
           - POs processed: {week_data['pos_processed']}
           - Savings: ${week_data['total_savings']}
           - Match rate: {week_data['match_rate']}%
           - Top mismatched items: {week_data['top_mismatches']}
           
           Keep it under 100 words and highlight key actions.
           """
           
           response = self.openai_client.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "You are a helpful assistant."},
                   {"role": "user", "content": prompt}
               ]
           )
           
           summary = response.choices[0].message.content
           
           # Create notification
           self.create_notification(
               user_id=user_id,
               type='weekly_summary',
               title='Your Weekly OrderGuard Summary',
               message=summary,
               ai_generated=True
           )
   ```

### Step 6: Performance Optimization with Caching

1. **Add caching layer with AI predictions**
   ```python
   # utils/ai_cache.py
   import redis
   import json
   from functools import wraps
   from datetime import timedelta
   
   redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
   
   class AICache:
       def __init__(self):
           self.redis = redis_client
       
       def cache_embedding(self, text: str, embedding: list, ttl: int = 86400):
           """Cache embeddings to avoid regeneration"""
           key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
           self.redis.setex(
               key,
               ttl,
               json.dumps(embedding)
           )
       
       def get_cached_embedding(self, text: str):
           """Retrieve cached embedding if available"""
           key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
           cached = self.redis.get(key)
           if cached:
               return json.loads(cached)
           return None
       
       def predictive_cache_warm(self, organization_id):
           """Pre-cache likely searches based on history"""
           # Get common searches
           common_searches = self.supabase.table('search_queries').select(
               'query'
           ).eq('organization_id', organization_id).order(
               'created_at', desc=True
           ).limit(20).execute()
           
           # Pre-generate embeddings for common searches
           for search in common_searches.data:
               if not self.get_cached_embedding(search['query']):
                   embedding = self.generate_embedding(search['query'])
                   self.cache_embedding(search['query'], embedding)
   ```

### Step 7: Enhanced UI Components with AI Features

1. **Create AI-powered dashboard components**
   ```javascript
   // static/js/ai-dashboard.js
   class AIDashboard {
       constructor() {
           this.initAIFeatures();
       }
       
       initAIFeatures() {
           // Semantic search interface
           this.initSemanticSearch();
           
           // AI insights panel
           this.loadAIInsights();
           
           // Real-time anomaly alerts
           this.subscribeToAnomalies();
       }
       
       async initSemanticSearch() {
           const searchInput = document.getElementById('semantic-search');
           const searchResults = document.getElementById('search-results');
           
           searchInput.addEventListener('input', debounce(async (e) => {
               const query = e.target.value;
               if (query.length < 3) return;
               
               const response = await fetch('/api/search/semantic', {
                   method: 'POST',
                   headers: {'Content-Type': 'application/json'},
                   body: JSON.stringify({
                       query: query,
                       price_book_id: getCurrentPriceBookId()
                   })
               });
               
               const data = await response.json();
               this.displaySearchResults(data.results);
           }, 300));
       }
       
       async loadAIInsights() {
           const response = await fetch('/api/analytics/insights');
           const insights = await response.json();
           
           const insightsPanel = document.getElementById('ai-insights');
           insightsPanel.innerHTML = `
               <div class="ai-insights-card">
                   <h3>AI Insights</h3>
                   <div class="insight-content">${insights.summary}</div>
                   <small>Generated: ${new Date(insights.generated_at).toLocaleString()}</small>
               </div>
           `;
       }
       
       subscribeToAnomalies() {
           // Subscribe to real-time anomaly detection
           const channel = supabase
               .channel('anomalies')
               .on('postgres_changes', {
                   event: 'INSERT',
                   schema: 'public',
                   table: 'notifications',
                   filter: 'type=eq.price_anomaly'
               }, (payload) => {
                   this.showAnomalyAlert(payload.new);
               })
               .subscribe();
       }
   }
   ```

2. **AI-powered chat assistant**
   ```javascript
   // static/js/ai-assistant.js
   class AIAssistant {
       constructor() {
           this.messages = [];
           this.initChat();
       }
       
       async sendMessage(message) {
           // Add user message
           this.addMessage('user', message);
           
           // Send to AI endpoint
           const response = await fetch('/api/ai/chat', {
               method: 'POST',
               headers: {'Content-Type': 'application/json'},
               body: JSON.stringify({
                   message: message,
                   context: this.getContext()
               })
           });
           
           const data = await response.json();
           this.addMessage('assistant', data.response);
       }
       
       getContext() {
           // Include relevant context for the AI
           return {
               current_page: window.location.pathname,
               organization_id: getCurrentOrgId(),
               recent_activity: this.getRecentActivity()
           };
       }
   }
   ```

## Verification Checklist

- [ ] AI extensions enabled (vector, pgmq, pg_net, pg_cron)
- [ ] Automatic embeddings working
- [ ] Semantic search functional
- [ ] AI insights generating
- [ ] Analytics tables created
- [ ] Analytics service working
- [ ] Admin dashboard accessible
- [ ] Platform metrics accurate
- [ ] Bulk processing with AI matching
- [ ] Anomaly detection working
- [ ] Notifications with AI alerts
- [ ] Performance optimizations applied
- [ ] UI enhancements complete
- [ ] Real-time updates working

## AI Performance Benchmarks

- Embedding generation: < 1 second per item
- Semantic search: < 200ms response time
- AI insights generation: < 5 seconds
- Anomaly detection: Real-time
- Chat response: < 3 seconds

## Best Practices for AI Features

1. **Cost Management**
   - Cache embeddings aggressively
   - Batch API calls when possible
   - Use smaller models for simple tasks
   - Monitor API usage

2. **User Experience**
   - Show AI confidence scores
   - Provide fallback options
   - Allow users to correct AI suggestions
   - Make AI features optional

3. **Data Privacy**
   - Never send sensitive data to AI APIs
   - Use on-premise models when possible
   - Implement data retention policies
   - Audit AI usage

## Next Steps
Proceed to Phase 7: Production Deployment and Launch 