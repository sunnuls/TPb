# TPb Architecture

## Overview

TPb is built as a monorepo with three main packages:

1. **shared** - Common types, constants, and utilities
2. **backend** - Node.js + Express + Socket.io server
3. **frontend** - React + Vite client

## Technology Stack

### Backend
- **Runtime**: Node.js 20+
- **Framework**: Express.js
- **Real-time**: Socket.io
- **Language**: TypeScript
- **Database**: PostgreSQL (planned)
- **Cache**: Redis (planned)

### Frontend
- **Framework**: React 18+
- **Build**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Real-time**: Socket.io-client

### Shared
- **Language**: TypeScript
- **Purpose**: Type definitions and utilities shared between frontend and backend

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Overlay)                  │
│                  (React + TypeScript + Vite)                 │
├─────────────────────────────────────────────────────────────┤
│                    WebSocket Bridge Layer                     │
│              (Real-time Data Synchronization)                │
├─────────────────────────────────────────────────────────────┤
│                   Backend Service Layer                       │
│     (Node.js + Express + Socket.io)                         │
├─────────────────────────────────────────────────────────────┤
│                   Analytics Engine Layer                      │
│     (Equity Calc, GTO Engine, Statistical Analysis)         │
├─────────────────────────────────────────────────────────────┤
│                   Data Integration Layer                      │
│     (Game State Management, Action History)                 │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Backend Services

#### GameStateService
Manages active game state and action history.

Key methods:
- `initializeGame()` - Start new game
- `recordAction()` - Record player action
- `updateBoard()` - Update community cards
- `updateHoleCards()` - Update player cards

#### EquityService
Calculates equity for multiple hands.

Features:
- Monte Carlo simulation (100k iterations)
- Exact calculation for small scenarios
- Performance target: <100ms

#### GTOService
Provides GTO-based strategy recommendations.

Features:
- Mixed strategy frequencies
- Action recommendations
- EV comparisons

### Frontend Components

#### Overlay
Main container component.

#### TableView
Visual representation of poker table.

Features:
- Player positions
- Community cards
- Pot display
- Active player indicator

#### StatisticsPanel
Player statistics display.

Shows:
- VPIP (Voluntarily Put $ In Pot)
- PFR (Pre-flop Raise)
- Aggression factor
- Stack sizes

#### StrategyPanel
GTO recommendations display.

Shows:
- Primary recommendation
- Alternative actions
- Frequency distributions
- Reasoning

## Data Flow

1. **User Action** → Frontend emits WebSocket event
2. **Backend** receives event → Updates GameState
3. **Analytics** calculate equity/recommendations
4. **Backend** emits updated state → All connected clients
5. **Frontend** updates UI

## WebSocket Events

### Client → Server
- `initGame` - Initialize game
- `recordAction` - Record action
- `updateBoard` - Update board
- `updateHoleCards` - Update cards

### Server → Client
- `connected` - Connection confirmed
- `gameInitialized` - Game started
- `actionRecorded` - Action recorded
- `boardUpdated` - Board updated with analytics
- `error` - Error occurred

## Performance Targets

| Metric | Target |
|--------|--------|
| Equity calculation | <100ms |
| WebSocket latency | <50ms |
| Frontend render | <16.67ms (60 FPS) |
| Board update (end-to-end) | <200ms |

## Future Enhancements

1. **Database Integration** - PostgreSQL for persistent storage
2. **Authentication** - JWT-based auth
3. **Redis Cache** - For GTO tables and computed results
4. **Player Profiling** - Long-term statistics
5. **Hand History** - Import/export

