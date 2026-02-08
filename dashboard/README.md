# Enhanced Cognee Dashboard

**Version:** 1.0.0
**Status:** Backend API + Basic Frontend POC
**Date:** 2026-02-06

---

## Overview

The Enhanced Cognee Dashboard provides real-time visualization and management of memories, sessions, and system metrics. This implementation includes a FastAPI backend with a basic HTML/CSS/JavaScript frontend proof-of-concept.

## Architecture

### Backend API (FastAPI)

**Endpoints:**

**System:**
- `GET /health` - Health check
- `GET /api/stats` - System statistics
- `GET /api/stream` - SSE streaming for real-time updates

**Memories:**
- `GET /api/memories` - List memories (paginated, filtered)
- `GET /api/memories/{id}` - Get specific memory
- `POST /api/memories` - Add new memory

**Search:**
- `GET /api/search` - Search memories with token efficiency

**Sessions:**
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}` - Get session details
- `GET /api/timeline/{id}` - Get timeline context

**Structured Memory:**
- `GET /api/structured-stats` - Structured memory statistics

**Security:**
- `GET /api/security/user` - Get authenticated user

### Frontend (HTML/CSS/JS)

**Features:**
- Real-time statistics display
- Memory list with type/concept badges
- Search interface
- SSE streaming for live updates
- Responsive design

**Components:**
- Statistics grid (4 cards)
- Memory list with pagination
- Search box with real-time results
- Status indicator

## Installation

### Prerequisites

```bash
pip install fastapi uvicorn[standard] websockets ssestarlette
```

### Configuration

Set environment variables:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
POSTGRES_DB=cognee_db
POSTGRES_USER=cognee_user
POSTGRES_PASSWORD=cognee_password

# API
CORS_ORIGINS=http://localhost:3000
API_KEY=your_api_key_here

# Security
JWT_SECRET=your_jwt_secret_here
```

### Running the Dashboard

**Development:**

```bash
# Start the API server
python dashboard/dashboard_api.py

# Dashboard available at:
# http://localhost:8000 - Dashboard UI
# http://localhost:8000/docs - API documentation (Swagger UI)
```

**Production:**

```bash
# Run with gunicorn (production WSGI server)
gunicorn dashboard.dashboard_api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard/ ./dashboard/

EXPOSE 8000

CMD ["python", "dashboard_api.py"]
```

```yaml
# docker-compose.yml
services:
  dashboard:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres-enhanced
      - QDRANT_HOST=qdrant-enhanced
    depends_on:
      - postgres-enhanced
      - qdrant-enhanced
```

## Usage Examples

### Fetch Statistics

```bash
curl http://localhost:8000/api/stats
```

**Response:**
```json
{
  "total_memories": 1523,
  "total_sessions": 45,
  "active_sessions": 2,
  "avg_tokens_per_memory": 342.5,
  "token_efficiency_percent": 89.2,
  "database_status": {
    "postgresql": true,
    "qdrant": true,
    "neo4j": true,
    "redis": true
  },
  "server_uptime": "2:15:30"
}
```

### List Memories

```bash
curl http://localhost:8000/api/memories?limit=10&agent_id=claude-code
```

### Search Memories

```bash
curl http://localhost:8000/api/search?query=authentication&limit=5
```

### Get Timeline Context

```bash
curl http://localhost:8000/api/timeline/{memory-id}?before=3&after=3
```

### SSE Streaming

```javascript
const eventSource = new EventSource('http://localhost:8000/api/stream');

eventSource.addEventListener('message', (e) => {
    const data = JSON.parse(e.data);
    console.log('Update:', data);
});
```

## API Documentation

Interactive API documentation available at:

**Swagger UI:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

## Dashboard Features

### Phase 1: Basic Dashboard [OK] IMPLEMENTED

- [x] Memory list view
- [x] Search interface
- [x] System statistics panel
- [x] Real-time updates (SSE)

### Phase 2: Advanced Features [FUTURE IMPLEMENTATION]

- [ ] Timeline visualization
- [ ] Graph visualization (Neo4j)
- [ ] Filter by type/category
- [ ] Export functionality (JSON, CSV)

### Phase 3: Developer Tools [FUTURE IMPLEMENTATION]

- [ ] API documentation viewer
- [ ] MCP tool testing interface
- [ ] Database inspector
- [ ] Performance metrics dashboard

## Real-Time Updates

The dashboard uses Server-Sent Events (SSE) for real-time updates:

```javascript
// Auto-reconnect on disconnect
eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
    setTimeout(() => connectStream(), 5000);
};
```

**Update Events:**

- `memory_added` - New memory created
- `memory_updated` - Memory modified
- `session_started` - Session began
- `session_ended` - Session completed
- `stats_updated` - Statistics changed

## Security

### Authentication

JWT-based authentication required for protected endpoints:

```bash
curl -H "Authorization: Bearer <token>" \\
     http://localhost:8000/api/security/user
```

### CORS

CORS enabled for:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

Configure additional origins via environment variable.

### Rate Limiting

TODO: Implement rate limiting middleware to prevent abuse.

## Performance

### Caching

Statistics cached for 30 seconds to reduce database load.

### Pagination

Memory list endpoints support pagination:
- `limit` - Results per page (max 1000)
- `offset` - Number of results to skip

### Database Queries

Optimized queries with proper indexes:
- Foreign key indexes
- Composite indexes for filters
- GIN indexes for JSON/JSONB columns

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-06T12:00:00Z",
  "version": "1.0.0"
}
```

### Logs

Application logs output to console. Configure log level:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Troubleshooting

### Issue: Dashboard Not Loading

**Check:**
- API server running: `curl http://localhost:8000/health`
- Browser console for errors
- Network tab for failed requests

**Solution:**
- Ensure backend is started
- Check CORS configuration
- Verify database connections

### Issue: Real-Time Updates Not Working

**Check:**
- SSE endpoint accessible: `curl http://localhost:8000/api/stream`
- Browser supports EventSource

**Solution:**
- Verify no proxy blocking SSE
- Check network firewall
- Review browser console errors

### Issue: High Memory Usage

**Check:**
- Number of active sessions
- Memory count
- Database connection pool size

**Solution:**
- Implement pagination
- Add connection pooling limits
- Cache frequently accessed data

## Development

### Running in Debug Mode

```bash
# Enable debug logging
LOGLEVEL=debug python dashboard/dashboard_api.py
```

### Hot Reload

```bash
# Install with dev dependencies
pip install uvicorn[standard]

# Run with auto-reload
uvicorn dashboard.dashboard_api:app --reload --port 8000
```

### Testing

Run tests with pytest:

```bash
pytest tests/dashboard/
```

## Future Enhancements

### Planned Features

1. **Advanced Visualizations**
   - Timeline view with interactive filtering
   - Graph visualization (Neo4j integration)
   - Heatmaps for activity

2. **User Management**
   - User authentication UI
   - Permission management
   - API key management interface

3. **Export/Import**
   - JSON export
   - CSV export
   - Bulk import
   - Data migration tools

4. **Advanced Search**
   - Faceted search
   - Saved searches
   - Search history
   - Advanced filters

5. **Monitoring**
   - Performance metrics dashboard
   - Query performance analysis
   - Error tracking
   - Alert system

---

**Generated:** 2026-02-06
**Enhanced Cognee Team**
**Status:** Backend API + Basic Frontend POC Complete
**Next:** Full Next.js Dashboard (Frontend Development)
