# TPb Setup Guide

## Prerequisites

- Node.js 20+ and npm 9+
- Docker and Docker Compose (optional but recommended)
- PostgreSQL 16+ (if running locally without Docker)
- Redis 7+ (if running locally without Docker)

## Installation

### Option 1: Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/sunnuls/TPb.git
cd TPb
```

2. Copy environment file:
```bash
copy .env.example .env
```

3. Start all services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3000
- Health check: http://localhost:3000/health

### Option 2: Local Development

1. Install dependencies for all packages:
```bash
npm install
```

2. Build shared package:
```bash
cd shared
npm run build
cd ..
```

3. Start PostgreSQL and Redis (if not using Docker):
```bash
# Using Docker for databases only
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

4. Start backend:
```bash
cd backend
npm install
npm run dev
```

5. Start frontend (in new terminal):
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file in the root directory:

```env
# Backend
NODE_ENV=development
PORT=3000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tpb_dev
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS
CORS_ORIGIN=http://localhost:5173

# Equity Engine
EQUITY_ITERATIONS=100000
EQUITY_METHOD=monte-carlo
```

## Verification

Test the API:
```bash
curl http://localhost:3000/health
```

Expected response:
```json
{
  "status": "healthy",
  "uptime": 123.456,
  "timestamp": "2026-01-14T...",
  "version": "0.1.0"
}
```

## Troubleshooting

### Port already in use
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Change port in .env
PORT=3001
```

### Database connection failed
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure port 5432 is not blocked

### WebSocket connection failed
- Check CORS settings
- Verify backend is running
- Check browser console for errors

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- See [API.md](./API.md) for API documentation
- Review [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines

