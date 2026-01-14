# TPb: Live-RTA Overlay Poker Assistant

![Status](https://img.shields.io/badge/status-in_development-yellow)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 Overview

TPb is a **real-time action (RTA) overlay assistant** designed for live poker stream analysis. Built with modern TypeScript stack (Node.js + React), it provides real-time player statistics, hand equity calculations, and Game Theory Optimal (GTO) strategy recommendations.

## ✨ Features

- 🎮 **Real-time game state tracking** via WebSocket
- 📊 **Player statistics** (VPIP, PFR, Aggression)
- 🃏 **Community card visualization**
- 🎯 **Hand equity calculations** (Monte Carlo, <100ms)
- 🧠 **GTO strategy recommendations**
- 📈 **Multi-table support** (planned)
- 🎨 **Stream-friendly UI overlay**

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Docker & Docker Compose (recommended)
- Git

### Installation

```bash
# 1. Clone repository
git clone https://github.com/sunnuls/TPb.git
cd TPb

# 2. Copy environment file
copy .env.example .env

# 3. Start with Docker Compose
docker-compose up -d

# 4. Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:3000
# Health: http://localhost:3000/health
```

### Local Development (without Docker)

```bash
# Install all dependencies
npm install

# Build shared package
cd shared && npm run build && cd ..

# Terminal 1: Backend
cd backend && npm run dev

# Terminal 2: Frontend
cd frontend && npm run dev
```

## 📁 Project Structure

```
TPb/
├── backend/              # Node.js + Express + Socket.io server
│   ├── src/
│   │   ├── services/     # Business logic (GameState, Equity, GTO)
│   │   ├── engines/      # Equity calculation engine
│   │   ├── controllers/  # REST API controllers
│   │   ├── websocket.ts  # WebSocket event handlers
│   │   ├── db/           # PostgreSQL schema & migrations
│   │   └── utils/        # Logging, validators
│   └── docker/           # Backend Dockerfile
├── frontend/             # React + Vite client
│   ├── src/
│   │   ├── components/   # UI components (Overlay, TableView, etc.)
│   │   ├── hooks/        # React hooks (useWebSocket, etc.)
│   │   ├── stores/       # Zustand state management
│   │   └── styles/       # Tailwind CSS styles
│   └── docker/           # Frontend Dockerfile + nginx
├── shared/               # Shared TypeScript types & utilities
│   └── src/
│       ├── types/        # Poker types, WebSocket events, API types
│       ├── constants/    # Cards, positions, limits
│       └── utils/        # Card utils, validators
├── docs/                 # Documentation
│   ├── SETUP.md         # Installation guide
│   ├── API.md           # API documentation
│   ├── ARCHITECTURE.md  # System design
│   └── CONTRIBUTING.md  # Contribution guidelines
├── coach_app/           # Legacy Python/FastAPI code (see README.md)
├── docker-compose.yml   # Docker orchestration
├── package.json         # Root workspace config
└── ROADMAP.md          # Development roadmap
```

## 🏗️ Tech Stack

### Backend
- **Runtime**: Node.js 20+
- **Framework**: Express.js
- **Real-time**: Socket.io
- **Language**: TypeScript
- **Database**: PostgreSQL (with migrations)
- **Cache**: Redis (planned)

### Frontend
- **Framework**: React 18+
- **Build**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS + CSS Modules
- **State**: Zustand
- **Real-time**: Socket.io-client

### Shared
- TypeScript types & utilities
- Shared between frontend & backend

## 📡 API Overview

### REST Endpoints

```bash
GET  /health                    # Health check
GET  /api/game/current          # Current game state
GET  /api/game/history          # Full action history
GET  /api/game/history/:street  # Street-specific actions
GET  /api/player/:idx/stats     # Player statistics
GET  /api/config                # Configuration
```

### WebSocket Events

**Client → Server:**
- `initGame` - Initialize new game
- `recordAction` - Record player action
- `updateBoard` - Update community cards
- `updateHoleCards` - Update player hole cards
- `requestEquity` - Request equity calculation
- `requestRecommendation` - Request GTO recommendation

**Server → Client:**
- `connected` - Connection confirmed
- `gameInitialized` - Game started
- `actionRecorded` - Action recorded
- `boardUpdated` - Board updated with equity & recommendations
- `playerUpdated` - Player state updated
- `error` - Error occurred
- `heartbeat` - Connection health check

## 📊 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Equity calculation | <100ms | ✅ |
| WebSocket latency | <50ms | ✅ |
| Frontend render | <16.67ms (60 FPS) | ✅ |
| Board update (end-to-end) | <200ms | 🚧 |

## 📚 Documentation

- 📘 [**Setup Guide**](./docs/SETUP.md) - Detailed installation
- 🏗️ [**Architecture**](./docs/ARCHITECTURE.md) - System design
- 📡 [**API Documentation**](./docs/API.md) - REST & WebSocket API
- 🤝 [**Contributing**](./docs/CONTRIBUTING.md) - How to contribute
- 🗺️ [**Roadmap**](./ROADMAP.md) - Development plan

## 🛠️ Development

### Run Tests

```bash
# Backend tests
cd backend && npm test

# Frontend tests
cd frontend && npm test

# With coverage
npm run test:coverage
```

### Linting

```bash
npm run lint
```

### Database Migrations

```bash
cd backend && npm run migrate
```

## 🗺️ Roadmap

See [ROADMAP.md](./ROADMAP.md) for complete development plan.

**✅ Phase 1: Foundation & Core Services (Weeks 1-4)**
- [x] Monorepo structure
- [x] Backend setup (Express + Socket.io + TypeScript)
- [x] Frontend setup (React + Vite + TypeScript)
- [x] Shared types package
- [x] WebSocket communication
- [x] Equity calculation engine
- [x] Basic overlay UI
- [x] Database schema (PostgreSQL)
- [x] Docker configuration

**🚧 Phase 2: Core Poker Engine (Weeks 5-8)**
- [ ] Hand evaluation library
- [ ] Multi-way pot equity
- [ ] Range constructor
- [ ] GTO tables implementation
- [ ] Player statistics aggregation
- [ ] Action history parser

**📋 Phase 3: Stream Integration (Weeks 9-12)**
- [ ] Stream data parsers
- [ ] Real-time table state tracking
- [ ] Player action capture
- [ ] Notification system

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](./docs/CONTRIBUTING.md).

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

## 📞 Support

- 🐛 [Report Bugs](https://github.com/sunnuls/TPb/issues)
- 💡 [Feature Requests](https://github.com/sunnuls/TPb/discussions)
- 📧 Email: support@tpb.dev (planned)

---

## 📝 Legacy Python Code

> **Note:** The previous Python/FastAPI implementation is preserved in `coach_app/` directory. It includes a deterministic poker & blackjack coaching system. See [README.md](./README.md) for legacy documentation.

---

**Status:** In Development (v0.1.0)  
**Target Release:** Q2 2026  
**Last Updated:** 2026-01-14  
**Maintained by:** [@sunnuls](https://github.com/sunnuls)

