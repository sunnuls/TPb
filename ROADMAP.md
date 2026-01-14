# TPb: Live-RTA Overlay Poker Assistant - Development Roadmap

**Last Updated:** 2026-01-14  
**Status:** In Development  
**Target Release:** Q2 2026

---

## 1. Project Overview

TPb is a real-time action (RTA) overlay assistant designed for live poker stream analysis. It provides:
- Real-time player statistics and position analysis
- Community card visualization
- Hand equity calculations and recommendations
- Game theory optimal (GTO) strategy overlays
- Multi-table tournament (MTT) stack analysis
- Stream-friendly UI overlay

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Overlay)                  │
│                  (React + TypeScript + WebGL)                │
├─────────────────────────────────────────────────────────────┤
│                    WebSocket Bridge Layer                     │
│              (Real-time Data Synchronization)                │
├─────────────────────────────────────────────────────────────┤
│                   Backend Service Layer                       │
│     (Node.js + Express + Socket.io + Worker Threads)        │
├─────────────────────────────────────────────────────────────┤
│                   Analytics Engine Layer                      │
│     (Equity Calc, GTO Engine, Statistical Analysis)         │
├─────────────────────────────────────────────────────────────┤
│                   Data Integration Layer                      │
│     (Stream Parsers, Game State Management, Database)       │
├─────────────────────────────────────────────────────────────┤
│                   External Services Layer                     │
│     (Streaming APIs, PokerStars API, GTO Solvers, etc.)    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### Frontend
- **Overlay UI**: Real-time display of statistics, charts, and recommendations
- **Position Indicator**: Visual representation of player positions
- **Equity Display**: Real-time equity calculations with confidence bands
- **Strategy Panel**: GTO-based action recommendations
- **Settings Manager**: Theme, notification, and feature toggles

#### Backend
- **State Manager**: Centralized game state management
- **Equity Calculator**: Multi-way pot equity computations
- **GTO Engine**: Strategy recommendations based on position and stack depths
- **Data Parser**: Parse stream feeds, table information, and player actions
- **WebSocket Server**: Maintain real-time connections with frontend

#### Analytics
- **Statistical Analysis**: Player tendencies, fold-to-bet frequencies
- **Range Constructor**: Build opponent ranges based on action history
- **EV Calculator**: Expected value calculations for decisions
- **Simulation Engine**: Monte Carlo simulations for equity approximation

#### Data Layer
- **Game State Store**: In-memory cache of current game state
- **History DB**: PostgreSQL for game history and player stats
- **Config DB**: Solver results, GTO tables, and precomputed strategies

---

## 3. Project File Structure

```
TPb/
├── README.md
├── ROADMAP.md
├── package.json
├── tsconfig.json
├── jest.config.js
├── .env.example
│
├── backend/
│   ├── src/
│   │   ├── index.ts                 # Main entry point
│   │   ├── server.ts               # Express/Socket.io setup
│   │   │
│   │   ├── types/
│   │   │   ├── game.ts             # Game state interfaces
│   │   │   ├── player.ts           # Player data structures
│   │   │   ├── poker.ts            # Poker-specific types
│   │   │   └── websocket.ts        # WS message formats
│   │   │
│   │   ├── services/
│   │   │   ├── gameStateService.ts      # Game state management
│   │   │   ├── equityService.ts         # Equity calculations
│   │   │   ├── gtoService.ts            # GTO recommendations
│   │   │   ├── playerAnalysisService.ts # Player stat analysis
│   │   │   ├── streamParserService.ts   # Stream parsing
│   │   │   └── notificationService.ts   # Alert management
│   │   │
│   │   ├── controllers/
│   │   │   ├── gameController.ts    # Game endpoints
│   │   │   ├── playerController.ts  # Player endpoints
│   │   │   └── configController.ts  # Configuration endpoints
│   │   │
│   │   ├── parsers/
│   │   │   ├── streamParser.ts      # Stream format parsing
│   │   │   ├── tableParser.ts       # Table state parsing
│   │   │   └── actionParser.ts      # Action parsing
│   │   │
│   │   ├── engines/
│   │   │   ├── equityEngine.ts      # Equity calculation engine
│   │   │   ├── gtoEngine.ts         # GTO strategy engine
│   │   │   └── simulationEngine.ts  # Monte Carlo simulator
│   │   │
│   │   ├── db/
│   │   │   ├── connection.ts        # Database setup
│   │   │   ├── migrations/          # Database migrations
│   │   │   └── repositories/
│   │   │       ├── playerRepo.ts
│   │   │       ├── gameRepo.ts
│   │   │       └── statsRepo.ts
│   │   │
│   │   ├── utils/
│   │   │   ├── cardUtils.ts         # Card operations
│   │   │   ├── mathUtils.ts         # Mathematical helpers
│   │   │   ├── logger.ts            # Logging utility
│   │   │   └── validators.ts        # Input validators
│   │   │
│   │   ├── middleware/
│   │   │   ├── auth.ts              # Authentication
│   │   │   ├── errorHandler.ts      # Error handling
│   │   │   └── rateLimiter.ts       # Rate limiting
│   │   │
│   │   └── workers/
│   │       ├── equityWorker.ts      # Heavy computation worker
│   │       └── simulationWorker.ts  # Simulation worker
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── performance/
│   │
│   └── docker/
│       └── Dockerfile.backend
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── vite-env.d.ts
│   │   │
│   │   ├── types/
│   │   │   ├── game.ts
│   │   │   ├── ui.ts
│   │   │   └── api.ts
│   │   │
│   │   ├── components/
│   │   │   ├── Overlay/
│   │   │   │   ├── Overlay.tsx
│   │   │   │   └── Overlay.module.css
│   │   │   │
│   │   │   ├── TableView/
│   │   │   │   ├── TableView.tsx
│   │   │   │   ├── PlayerPosition.tsx
│   │   │   │   ├── CommunityCards.tsx
│   │   │   │   └── TableView.module.css
│   │   │   │
│   │   │   ├── StatisticsPanel/
│   │   │   │   ├── StatisticsPanel.tsx
│   │   │   │   ├── EquityDisplay.tsx
│   │   │   │   ├── RangeChart.tsx
│   │   │   │   └── Stats.module.css
│   │   │   │
│   │   │   ├── StrategyPanel/
│   │   │   │   ├── StrategyPanel.tsx
│   │   │   │   ├── RecommendationCard.tsx
│   │   │   │   └── Strategy.module.css
│   │   │   │
│   │   │   ├── SettingsPanel/
│   │   │   │   ├── SettingsPanel.tsx
│   │   │   │   ├── ThemeToggle.tsx
│   │   │   │   └── Settings.module.css
│   │   │   │
│   │   │   └── Common/
│   │   │       ├── Card.tsx
│   │   │       ├── Badge.tsx
│   │   │       └── Spinner.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useGameState.ts      # Game state hook
│   │   │   ├── useWebSocket.ts      # WS connection hook
│   │   │   ├── useEquityCalc.ts     # Equity calculation hook
│   │   │   └── useLocalStorage.ts   # Local storage hook
│   │   │
│   │   ├── services/
│   │   │   ├── websocketService.ts  # WS client
│   │   │   ├── apiService.ts        # API client
│   │   │   ├── storageService.ts    # Local storage
│   │   │   └── themeService.ts      # Theme management
│   │   │
│   │   ├── utils/
│   │   │   ├── cardUtils.ts
│   │   │   ├── formatters.ts
│   │   │   └── validators.ts
│   │   │
│   │   ├── styles/
│   │   │   ├── globals.css
│   │   │   ├── variables.css
│   │   │   └── animations.css
│   │   │
│   │   └── constants/
│   │       ├── gameConstants.ts
│   │       ├── uiConstants.ts
│   │       └── messages.ts
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── docker/
│       └── Dockerfile.frontend
│
├── shared/
│   ├── src/
│   │   ├── types/
│   │   │   ├── poker.ts            # Shared poker types
│   │   │   ├── websocket.ts        # Shared WS types
│   │   │   └── api.ts              # Shared API types
│   │   │
│   │   ├── constants/
│   │   │   ├── cards.ts
│   │   │   ├── positions.ts
│   │   │   └── limits.ts
│   │   │
│   │   └── utils/
│   │       ├── cardUtils.ts
│   │       └── validators.ts
│   │
│   └── package.json
│
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   ├── CONTRIBUTING.md
│   └── GTO_ENGINE.md
│
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── .env.example
```

---

## 4. Implementation Phases

### Phase 1: Foundation & Core Services (Weeks 1-4)

**Goals:**
- Set up project structure and build pipeline
- Implement core type system and utilities
- Build basic WebSocket infrastructure
- Create game state management

**Tasks:**
1. Initialize monorepo structure with shared types
2. Set up Express + Socket.io backend
3. Create React + TypeScript frontend scaffold
4. Implement game state interfaces
5. Build WebSocket communication layer
6. Create database schema
7. Set up CI/CD pipeline

**Deliverables:**
- Working project scaffold
- Type system foundations
- Basic WebSocket communication
- Development environment documentation

### Phase 2: Core Poker Engine (Weeks 5-8)

**Goals:**
- Implement equity calculation engine
- Build card and hand evaluation utilities
- Create basic strategy recommendation system
- Develop player analysis framework

**Tasks:**
1. Implement Omaha/Texas Hold'em hand evaluation
2. Build equity calculator with multi-way pot support
3. Create range constructor for opponent modeling
4. Implement basic GTO tables for common scenarios
5. Build player statistics aggregation
6. Create action history parser

**Deliverables:**
- Functional equity calculator (accurate to 4 decimal places)
- Hand evaluation library
- Basic GTO recommendations
- Player stat tracking

### Phase 3: Stream Integration & Parsers (Weeks 9-12)

**Goals:**
- Implement stream data parsers
- Build real-time table state tracking
- Create player action capture system
- Develop notification system

**Tasks:**
1. Build stream feed parsers (generic format)
2. Implement OCR for real table states
3. Create action capture and validation
4. Build notification/alert system
5. Implement player position tracking
6. Create hand history capture

**Deliverables:**
- Working stream parser
- Real-time table state tracking
- Player action capture
- Basic notification system

### Phase 4: Frontend Overlay UI (Weeks 13-16)

**Goals:**
- Build responsive overlay UI
- Create visualization components
- Implement settings and customization
- Build performance-optimized rendering

**Tasks:**
1. Create main overlay component
2. Build table visualization
3. Implement statistics panel
4. Create strategy recommendation display
5. Build settings/configuration UI
6. Optimize rendering performance
7. Add theme system

**Deliverables:**
- Complete overlay UI
- All visualization components
- Settings panel
- Performance optimized (<60ms latency)

### Phase 5: Advanced Analytics (Weeks 17-20)

**Goals:**
- Implement advanced statistical analysis
- Build trend detection
- Create exploitative strategy recommendations
- Develop player profiling

**Tasks:**
1. Build advanced statistical analysis engine
2. Implement trend detection algorithms
3. Create exploitative strategy layer
4. Build player tendency profiler
5. Implement variance analysis
6. Create leakfinder algorithms

**Deliverables:**
- Advanced analytics engine
- Player profiling system
- Exploitative recommendations
- Trend detection system

### Phase 6: Multi-Table & Tournament Mode (Weeks 21-24)

**Goals:**
- Implement multi-table tournament support
- Build stack depth analysis
- Create ICM calculations
- Develop tournament strategy overlays

**Tasks:**
1. Build multi-table state manager
2. Implement ICM calculations
3. Create chip EV to cash EV converter
4. Build tournament strategy recommendations
5. Implement blind progression tracking
6. Create payout structure analyzer

**Deliverables:**
- Multi-table support
- ICM calculator
- Tournament strategy recommendations
- Stack depth analysis

### Phase 7: Testing & Optimization (Weeks 25-26)

**Goals:**
- Comprehensive test coverage
- Performance optimization
- Security hardening
- Load testing

**Tasks:**
1. Write comprehensive test suite (>80% coverage)
2. Performance profiling and optimization
3. Security audit
4. Load testing
5. Documentation completion
6. Release preparation

**Deliverables:**
- >80% test coverage
- Performance benchmarks
- Security report
- Complete documentation
- v1.0.0 release

---

## 5. Technology Stack

### Backend
- **Runtime**: Node.js 20+
- **Framework**: Express.js
- **Real-time**: Socket.io
- **Language**: TypeScript
- **Database**: PostgreSQL (primary), Redis (caching)
- **Workers**: Worker Threads for heavy computation
- **Testing**: Jest + Supertest

### Frontend
- **Framework**: React 18+
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + CSS Modules
- **State**: React Hooks + Context API (or Zustand)
- **Real-time**: Socket.io-client
- **Testing**: Vitest + React Testing Library
- **Charts**: Recharts or Chart.js

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Optional Kubernetes support
- **CI/CD**: GitHub Actions
- **Monitoring**: Optional Prometheus + Grafana
- **Logging**: Winston + ELK Stack (optional)

---

## 6. Code Examples

### 6.1 Backend: Core Equity Calculator

```typescript
// backend/src/engines/equityEngine.ts

import { Card, Hand, Equity } from '../types/poker';
import { cardToIndex, cardsToMask } from '../utils/cardUtils';

export interface EquityCalculatorOptions {
  maxIterations?: number;
  precision?: number;
  method?: 'exact' | 'monte-carlo';
}

export class EquityEngine {
  private readonly iterations: number;
  private readonly precision: number;
  private readonly method: 'exact' | 'monte-carlo';

  constructor(options: EquityCalculatorOptions = {}) {
    this.iterations = options.maxIterations || 100000;
    this.precision = options.precision || 4;
    this.method = options.method || 'monte-carlo';
  }

  /**
   * Calculate equity for multiple hands
   * @param hands - Array of player hands [cards, ...]
   * @param board - Community cards on board (0-5 cards)
   * @param dead - Dead cards
   * @returns Equity percentages for each hand
   */
  calculateEquity(
    hands: Card[][],
    board: Card[],
    dead: Card[] = []
  ): Equity[] {
    if (this.method === 'exact' && board.length >= 3) {
      return this.calculateExactEquity(hands, board, dead);
    }
    return this.calculateMonteCarloEquity(hands, board, dead);
  }

  private calculateExactEquity(
    hands: Card[][],
    board: Card[],
    dead: Card[]
  ): Equity[] {
    const numHands = hands.length;
    const wins = new Array(numHands).fill(0);
    const ties = new Array(numHands).fill(0);
    const losses = new Array(numHands).fill(0);
    let totalOutcomes = 0;

    const usedCards = new Set<string>();
    hands.forEach(hand => hand.forEach(card => usedCards.add(card)));
    board.forEach(card => usedCards.add(card));
    dead.forEach(card => usedCards.add(card));

    const remainingCards = this.getRemainingCards(usedCards);
    const boardSize = board.length;
    const neededCards = 5 - boardSize;

    // Generate all possible boards
    const possibleBoards = this.generateCombinations(remainingCards, neededCards);

    possibleBoards.forEach(boardAddition => {
      const finalBoard = [...board, ...boardAddition];
      const handStrengths = hands.map(hand => this.evaluateHand(hand, finalBoard));
      const maxStrength = Math.max(...handStrengths);

      handStrengths.forEach((strength, idx) => {
        if (strength === maxStrength) {
          const tiePlayers = handStrengths.filter(s => s === strength).length;
          ties[idx] += 1 / tiePlayers;
        } else if (strength > 0) {
          losses[idx] += 1;
        }
      });

      totalOutcomes++;
    });

    return hands.map((_, idx) => ({
      equity: Number((ties[idx] / totalOutcomes).toFixed(this.precision)),
      confidence: 1.0,
      wins: wins[idx],
      ties: ties[idx],
      losses: losses[idx],
    }));
  }

  private calculateMonteCarloEquity(
    hands: Card[][],
    board: Card[],
    dead: Card[]
  ): Equity[] {
    const numHands = hands.length;
    const wins = new Array(numHands).fill(0);
    const ties = new Array(numHands).fill(0);

    const usedCards = new Set<string>();
    hands.forEach(hand => hand.forEach(card => usedCards.add(card)));
    board.forEach(card => usedCards.add(card));
    dead.forEach(card => usedCards.add(card));

    const remainingCards = this.getRemainingCards(usedCards);
    const boardSize = board.length;
    const neededCards = 5 - boardSize;

    for (let i = 0; i < this.iterations; i++) {
      const randomBoard = this.getRandomSample(remainingCards, neededCards);
      const finalBoard = [...board, ...randomBoard];
      const handStrengths = hands.map(hand => this.evaluateHand(hand, finalBoard));
      const maxStrength = Math.max(...handStrengths);

      handStrengths.forEach((strength, idx) => {
        if (strength === maxStrength) {
          const tiePlayers = handStrengths.filter(s => s === strength).length;
          ties[idx] += 1 / tiePlayers;
        }
      });
    }

    const variance = this.estimateVariance(ties, this.iterations);
    const stdError = Math.sqrt(variance / this.iterations);

    return hands.map((_, idx) => ({
      equity: Number((ties[idx] / this.iterations).toFixed(this.precision)),
      confidence: this.calculateConfidence(stdError),
      wins: ties[idx],
      ties: 0,
      losses: this.iterations - ties[idx],
    }));
  }

  private evaluateHand(hand: Card[], board: Card[]): number {
    // Implement hand evaluation (returns strength ranking)
    // This would use a lookup table or fast hand evaluator
    const allCards = [...hand, ...board];
    return this.rankHand(allCards);
  }

  private rankHand(cards: Card[]): number {
    // Placeholder for hand ranking logic
    // In production, use a fast hand evaluator like TwoPlusTwoEvaluator
    return 0;
  }

  private generateCombinations(cards: Card[], k: number): Card[][] {
    // Generate all k-combinations of cards
    const result: Card[][] = [];
    const n = cards.length;

    const helper = (start: number, combo: Card[]) => {
      if (combo.length === k) {
        result.push([...combo]);
        return;
      }
      for (let i = start; i < n; i++) {
        combo.push(cards[i]);
        helper(i + 1, combo);
        combo.pop();
      }
    };

    helper(0, []);
    return result;
  }

  private getRandomSample(cards: Card[], k: number): Card[] {
    const sample: Card[] = [];
    const available = [...cards];

    for (let i = 0; i < k && available.length > 0; i++) {
      const idx = Math.floor(Math.random() * available.length);
      sample.push(available[idx]);
      available.splice(idx, 1);
    }

    return sample;
  }

  private getRemainingCards(usedCards: Set<string>): Card[] {
    const allCards = this.getAllCards();
    return allCards.filter(card => !usedCards.has(card));
  }

  private getAllCards(): Card[] {
    const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    const suits = ['s', 'h', 'd', 'c'];
    const cards: Card[] = [];

    for (const rank of ranks) {
      for (const suit of suits) {
        cards.push(`${rank}${suit}` as Card);
      }
    }

    return cards;
  }

  private estimateVariance(values: number[], n: number): number {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const squaredDiffs = values.map(v => Math.pow(v / n - mean, 2));
    return squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  }

  private calculateConfidence(stdError: number): number {
    return Math.max(0, 1 - stdError);
  }
}
```

### 6.2 Backend: Game State Service

```typescript
// backend/src/services/gameStateService.ts

import { GameState, PlayerState, Action } from '../types/game';
import { Card, Position } from '../types/poker';
import { EventEmitter } from 'events';

export class GameStateService extends EventEmitter {
  private gameState: GameState | null = null;
  private actionHistory: Action[] = [];
  private maxHistorySize = 10000;

  /**
   * Initialize a new game
   */
  initializeGame(
    players: PlayerState[],
    buttonPosition: Position,
    smallBlind: number,
    bigBlind: number
  ): GameState {
    this.gameState = {
      id: this.generateGameId(),
      players,
      buttonPosition,
      blinds: { small: smallBlind, big: bigBlind },
      pot: 0,
      board: [],
      street: 'preflop',
      currentPlayerIdx: this.getSmallBlindPosition(players, buttonPosition),
      createdAt: new Date(),
      updatedAt: new Date(),
      status: 'active',
    };

    this.actionHistory = [];
    this.emit('gameInitialized', this.gameState);
    return this.gameState;
  }

  /**
   * Record a player action
   */
  recordAction(
    playerIdx: number,
    action: 'fold' | 'check' | 'call' | 'raise' | 'all-in' | 'bet',
    amount: number = 0
  ): Action {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    const newAction: Action = {
      playerIdx,
      action,
      amount,
      timestamp: new Date(),
      street: this.gameState.street,
      potAtAction: this.gameState.pot,
      stackAtAction: this.gameState.players[playerIdx].stack,
    };

    this.actionHistory.push(newAction);
    this.trimHistory();

    // Update player state
    const player = this.gameState.players[playerIdx];
    if (action === 'fold') {
      player.folded = true;
    } else if (action !== 'check') {
      player.stack -= amount;
      this.gameState.pot += amount;
    }

    this.gameState.updatedAt = new Date();
    this.emit('actionRecorded', newAction);

    return newAction;
  }

  /**
   * Update community cards (board)
   */
  updateBoard(cards: Card[], street: 'flop' | 'turn' | 'river'): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    this.gameState.board = cards;
    this.gameState.street = street;
    this.gameState.updatedAt = new Date();

    this.emit('boardUpdated', { cards, street });
  }

  /**
   * Update hole cards for a player (typically hero)
   */
  updateHoleCards(playerIdx: number, cards: Card[]): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    this.gameState.players[playerIdx].holeCards = cards;
    this.gameState.updatedAt = new Date();

    this.emit('holeCardsUpdated', { playerIdx, cards });
  }

  /**
   * Get current game state
   */
  getCurrentGame(): GameState | null {
    return this.gameState;
  }

  /**
   * Get action history for a specific player
   */
  getPlayerActionHistory(playerIdx: number): Action[] {
    return this.actionHistory.filter(action => action.playerIdx === playerIdx);
  }

  /**
   * Get actions on a specific street
   */
  getStreetActions(street: string): Action[] {
    return this.actionHistory.filter(action => action.street === street);
  }

  /**
   * Get all actions in chronological order
   */
  getFullHistory(): Action[] {
    return [...this.actionHistory];
  }

  /**
   * End current game
   */
  endGame(winner: number, winAmount: number): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    this.gameState.status = 'completed';
    this.gameState.updatedAt = new Date();

    this.emit('gameEnded', {
      gameId: this.gameState.id,
      winner,
      winAmount,
    });
  }

  private getSmallBlindPosition(players: PlayerState[], buttonPosition: Position): number {
    const positions = ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'];
    const currentIdx = positions.indexOf(buttonPosition);
    return (currentIdx + 1) % players.length;
  }

  private generateGameId(): string {
    return `game_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private trimHistory(): void {
    if (this.actionHistory.length > this.maxHistorySize) {
      this.actionHistory = this.actionHistory.slice(-this.maxHistorySize);
    }
  }
}
```

### 6.3 Backend: WebSocket Handler

```typescript
// backend/src/server.ts

import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { GameStateService } from './services/gameStateService';
import { EquityEngine } from './engines/equityEngine';
import { GTOEngine } from './engines/gtoEngine';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: { origin: '*' },
  transports: ['websocket', 'polling'],
});

// Initialize services
const gameStateService = new GameStateService();
const equityEngine = new EquityEngine({ method: 'monte-carlo' });
const gtoEngine = new GTOEngine();

// Middleware
app.use(express.json());

// WebSocket handlers
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);

  socket.on('initGame', (data) => {
    try {
      const gameState = gameStateService.initializeGame(
        data.players,
        data.buttonPosition,
        data.smallBlind,
        data.bigBlind
      );

      socket.emit('gameInitialized', gameState);
      socket.broadcast.emit('gameInitialized', gameState);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });

  socket.on('recordAction', (data) => {
    try {
      const action = gameStateService.recordAction(
        data.playerIdx,
        data.action,
        data.amount
      );

      const gameState = gameStateService.getCurrentGame();
      io.emit('actionRecorded', { action, gameState });
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });

  socket.on('updateBoard', (data) => {
    try {
      gameStateService.updateBoard(data.cards, data.street);

      const gameState = gameStateService.getCurrentGame();
      if (gameState) {
        // Calculate equity for all players
        const equity = equityEngine.calculateEquity(
          gameState.players
            .filter(p => !p.folded && p.holeCards)
            .map(p => p.holeCards!),
          gameState.board
        );

        // Get GTO recommendations
        const recommendations = gtoEngine.getRecommendations(gameState);

        io.emit('boardUpdated', { gameState, equity, recommendations });
      }
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });

  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// REST API endpoints
app.get('/api/game/current', (req, res) => {
  const gameState = gameStateService.getCurrentGame();
  res.json(gameState || { error: 'No active game' });
});

app.get('/api/game/history', (req, res) => {
  const history = gameStateService.getFullHistory();
  res.json(history);
});

// Start server
const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### 6.4 Frontend: Overlay Component

```typescript
// frontend/src/components/Overlay/Overlay.tsx

import React, { useEffect, useState } from 'react';
import { useGameState } from '../../hooks/useGameState';
import { useWebSocket } from '../../hooks/useWebSocket';
import { TableView } from '../TableView/TableView';
import { StatisticsPanel } from '../StatisticsPanel/StatisticsPanel';
import { StrategyPanel } from '../StrategyPanel/StrategyPanel';
import { SettingsPanel } from '../SettingsPanel/SettingsPanel';
import styles from './Overlay.module.css';

export const Overlay: React.FC = () => {
  const { gameState, updateGameState } = useGameState();
  const { socket, isConnected } = useWebSocket();
  const [showSettings, setShowSettings] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'stats' | 'strategy' | 'settings'>('stats');

  useEffect(() => {
    if (!socket) return;

    socket.on('boardUpdated', (data) => {
      updateGameState(data.gameState);
    });

    socket.on('actionRecorded', (data) => {
      updateGameState(data.gameState);
    });

    socket.on('error', (data) => {
      console.error('Socket error:', data.message);
    });

    return () => {
      socket.off('boardUpdated');
      socket.off('actionRecorded');
      socket.off('error');
    };
  }, [socket]);

  if (!isConnected) {
    return (
      <div className={styles.connectionError}>
        <p>Connecting to server...</p>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className={styles.placeholder}>
        <p>Waiting for game data...</p>
      </div>
    );
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.container}>
        {/* Main Table View */}
        <div className={styles.mainPanel}>
          <TableView gameState={gameState} />
        </div>

        {/* Side Panels */}
        <div className={styles.sidePanels}>
          <div className={styles.tabButtons}>
            <button
              className={`${styles.tabBtn} ${selectedTab === 'stats' ? styles.active : ''}`}
              onClick={() => setSelectedTab('stats')}
            >
              Stats
            </button>
            <button
              className={`${styles.tabBtn} ${selectedTab === 'strategy' ? styles.active : ''}`}
              onClick={() => setSelectedTab('strategy')}
            >
              Strategy
            </button>
            <button
              className={`${styles.tabBtn} ${selectedTab === 'settings' ? styles.active : ''}`}
              onClick={() => setSelectedTab('settings')}
            >
              ⚙️
            </button>
          </div>

          {selectedTab === 'stats' && <StatisticsPanel gameState={gameState} />}
          {selectedTab === 'strategy' && <StrategyPanel gameState={gameState} />}
          {selectedTab === 'settings' && <SettingsPanel />}
        </div>
      </div>
    </div>
  );
};
```

### 6.5 Frontend: Custom Hook for Game State

```typescript
// frontend/src/hooks/useGameState.ts

import { useState, useCallback } from 'react';
import { GameState } from '../types/game';

interface GameStateContextType {
  gameState: GameState | null;
  updateGameState: (newState: Partial<GameState>) => void;
  clearGameState: () => void;
}

export const useGameState = (): GameStateContextType => {
  const [gameState, setGameState] = useState<GameState | null>(null);

  const updateGameState = useCallback((newState: Partial<GameState>) => {
    setGameState(prev => (prev ? { ...prev, ...newState } : null));
  }, []);

  const clearGameState = useCallback(() => {
    setGameState(null);
  }, []);

  return { gameState, updateGameState, clearGameState };
};
```

### 6.6 Shared Types

```typescript
// shared/src/types/poker.ts

export type Card = `${Rank}${Suit}`;
export type Rank = 'A' | 'K' | 'Q' | 'J' | 'T' | '9' | '8' | '7' | '6' | '5' | '4' | '3' | '2';
export type Suit = 's' | 'h' | 'd' | 'c'; // spades, hearts, diamonds, clubs

export type Position = 'BTN' | 'SB' | 'BB' | 'UTG' | 'UTG+1' | 'MP' | 'HJ' | 'CO';

export interface Hand {
  card1: Card;
  card2: Card;
}

export interface Equity {
  equity: number; // 0-1
  confidence: number; // 0-1
  wins: number;
  ties: number;
  losses: number;
}

export interface Range {
  [hand: string]: number; // hand -> percentage weight
}

export interface HandStrength {
  hand: Hand;
  strength: number; // 0-1 (strength ranking)
  rank: string; // e.g., "pair of aces"
}
```

---

## 7. Performance Targets

| Metric | Target | Priority |
|--------|--------|----------|
| Equity calculation latency | <100ms (100k iterations) | High |
| WebSocket message latency | <50ms | High |
| Frontend render time | <16.67ms (60 FPS) | High |
| Board state update | <200ms end-to-end | Medium |
| GTO recommendation lookup | <50ms | Medium |
| Memory usage (backend) | <500MB average | Medium |
| Memory usage (frontend) | <100MB | Low |

---

## 8. Security Considerations

1. **Input Validation**: All inputs validated on both frontend and backend
2. **Rate Limiting**: Implement rate limiting on WebSocket connections
3. **Authentication**: JWT-based authentication for protected endpoints
4. **HTTPS/WSS**: Encrypt all communications in production
5. **Data Sanitization**: All user inputs sanitized before processing
6. **Error Handling**: Don't expose sensitive information in error messages
7. **CORS**: Properly configured CORS headers

---

## 9. Testing Strategy

### Unit Tests
- Equity calculator precision and performance
- Card utility functions
- Hand evaluation
- Position calculations

### Integration Tests
- WebSocket communication
- Game state management
- Database operations
- API endpoints

### E2E Tests
- Full game flow
- Overlay UI interactions
- Settings persistence
- Real-time updates

### Performance Tests
- Equity calculation benchmarks
- WebSocket throughput
- Memory usage profiles
- Frontend rendering performance

---

## 10. Deployment Strategy

### Development
```bash
docker-compose up -d
```

### Staging
- Deploy to staging environment
- Run full test suite
- Performance benchmarking
- Security scanning

### Production
- Docker multi-stage builds
- Health checks and monitoring
- Horizontal scaling ready
- Database backups
- CDN for static assets

---

## 11. Future Enhancements (Post v1.0)

1. **Machine Learning Integration**
   - Opponent pattern prediction
   - Hand range inference
   - Exploitative adaptation

2. **Advanced Solvers**
   - Pokersolver integration
   - Custom GTO tables
   - Position-specific solvers

3. **Mobile Support**
   - Responsive overlay
   - Mobile-friendly UI
   - Mobile app (native)

4. **Multi-Format Support**
   - Cash game optimization
   - Tournament-specific features
   - SNGs and spins

5. **Live Integration**
   - PokerStars API integration
   - Twitch chat integration
   - Real-time viewer sync

6. **Analytics Dashboard**
   - Game statistics
   - Win rate tracking
   - ROI calculations
   - Downswing analysis

---

## 12. Getting Started

See [SETUP.md](./docs/SETUP.md) for detailed setup instructions.

### Quick Start
```bash
# Clone repository
git clone https://github.com/sunnuls/TPb.git
cd TPb

# Install dependencies
npm install

# Start development environment
docker-compose up -d

# Start backend
cd backend && npm start

# Start frontend (in new terminal)
cd frontend && npm run dev
```

---

## 13. Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md) for contribution guidelines.

---

## 14. License

MIT License - See LICENSE file for details

---

## 15. Support & Feedback

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Share ideas in GitHub Discussions
- **Email**: support@tpb.dev (future)

---

**Last Updated:** 2026-01-14  
**Maintained by:** @sunnuls
