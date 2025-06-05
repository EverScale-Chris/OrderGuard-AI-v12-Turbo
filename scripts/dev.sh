#!/bin/bash

# OrderGuard AI Pro Development Script
# Starts the development environment with Supabase integration

echo "🚀 Starting OrderGuard AI Pro Development Environment"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
echo "📋 Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Check Supabase CLI
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Please install it first:"
    echo "   brew install supabase/tap/supabase"
    exit 1
fi

# Check if local Supabase is running
echo "🔍 Checking Supabase status..."
if ! supabase status &> /dev/null; then
    echo "🚀 Starting local Supabase..."
    supabase start
else
    echo "✅ Supabase is already running"
fi

# Verify Phase 1 setup
echo "🔍 Verifying Phase 1 setup..."
python migrations/runner.py verify

if [ $? -eq 0 ]; then
    echo "✅ Phase 1 verification passed"
else
    echo "⚠️  Phase 1 verification failed. Please check the setup."
    exit 1
fi

# Start Flask application
echo "🌐 Starting Flask application..."
echo "   App URL: ${APP_URL:-http://localhost:5000}"
echo "   Supabase URL: ${SUPABASE_URL}"
echo "   AI Features: ${ENABLE_AI_FEATURES:-false}"
echo ""
echo "Press Ctrl+C to stop the development server"
echo ""

python app.py 