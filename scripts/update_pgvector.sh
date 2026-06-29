#!/bin/bash

# pgVector Extension Update Script for PostgreSQL 18
# Updates pgVector to the latest version and verifies functionality

set -e

CONTAINER_NAME="postgres-enhanced-cognee"
DB_USER="cognee_user"
DB_NAME="cognee_db"

echo "=== pgVector Extension Update for PostgreSQL 18 ==="

# Check if PostgreSQL 18 is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "❌ PostgreSQL container is not running!"
    echo "Please start your RNR Enhanced Cognee stack with PostgreSQL 18 first"
    exit 1
fi

# Get current pgVector version
echo "🔍 Checking current pgVector version..."
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" || echo "Vector extension not found"

# Check PostgreSQL version
echo "🐘 Checking PostgreSQL version..."
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "SELECT version();"

# Update pgVector extension (PostgreSQL 18 includes latest pgVector)
echo "📦 Updating pgVector extension to latest version..."

# Create extension if it doesn't exist
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" || {
    echo "❌ Failed to create vector extension"
    exit 1
}

# Update to latest version
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "ALTER EXTENSION vector UPDATE;" || {
    echo "⚠️  Could not update vector extension (might already be latest)"
}

# Verify pgVector version after update
echo "✅ pgVector version after update:"
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

# Test pgVector functionality
echo "🧪 Testing pgVector functionality..."

docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "
DO \$\$
BEGIN
    -- Create test table with vector column
    CREATE TABLE IF NOT EXISTS pgvector_test (
        id SERIAL PRIMARY KEY,
        embedding VECTOR(3),
        description TEXT
    );

    -- Insert test data
    INSERT INTO pgvector_test (embedding, description)
    VALUES
        ('[1,2,3]', 'Test vector 1'),
        ('[4,5,6]', 'Test vector 2'),
        ('[1,1,1]', 'Test vector 3')
    ON CONFLICT DO NOTHING;

    -- Test vector similarity search
    CREATE INDEX IF NOT EXISTS pgvector_test_idx ON pgvector_test USING ivfflat (embedding vector_cosine_ops);

    -- Test query
    SELECT id, description, 1 - (embedding <=> '[1,2,3]') as similarity
    FROM pgvector_test
    ORDER BY similarity DESC
    LIMIT 3;

    RAISE NOTICE 'pgVector test completed successfully';
END \$\$;
"

echo ""
echo "🎉 pgVector update completed successfully!"
echo ""

# Show vector capabilities
echo "🔍 pgVector capabilities:"
docker exec $CONTAINER_NAME psql \
    -U $DB_USER \
    -d $DB_NAME \
    -c "
SELECT
    'Available pgVector functions:' as info,
    array_agg(proname) as functions
FROM pg_proc
WHERE proname LIKE '%vector%'
OR proname LIKE '%cosine%'
OR proname LIKE '%l2%'
OR proname LIKE '%inner%'
LIMIT 10;
"

echo ""
echo "📊 Performance improvements with PostgreSQL 18 + pgVector:"
echo "  ✅ Improved parallel query execution"
echo "  ✅ Better vector indexing performance"
echo "  ✅ Enhanced memory management for vector operations"
echo "  ✅ Faster similarity searches"
echo "  ✅ Improved pgVector integration"