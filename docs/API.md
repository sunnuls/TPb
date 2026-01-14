# TPb API Documentation

## Base URL

```
http://localhost:3000/api
```

## WebSocket

```
ws://localhost:3000
```

## Authentication

Currently no authentication required (development only).

## REST API Endpoints

### Health Check

**GET** `/health`

Response:
```json
{
  "status": "healthy",
  "uptime": 123.456,
  "version": "0.1.0",
  "services": {
    "database": true,
    "redis": true
  }
}
```

### Game State

**GET** `/api/game/current`

Get current active game state.

Response:
```json
{
  "success": true,
  "data": {
    "id": "game_1234567890_abc",
    "players": [...],
    "pot": 100,
    "board": ["As", "Kh", "Qd"],
    "street": "flop",
    ...
  },
  "timestamp": "2026-01-14T..."
}
```

**GET** `/api/game/history`

Get full action history.

**GET** `/api/game/history/:street`

Get actions for specific street (preflop, flop, turn, river).

### Player Stats

**GET** `/api/player/:playerIdx/history`

Get action history for specific player.

**GET** `/api/player/:playerIdx/stats`

Get statistics for specific player.

## WebSocket Events

### Client → Server

#### `initGame`

Initialize new game.

```typescript
socket.emit('initGame', {
  players: [
    { name: "Player 1", stack: 1000, position: "BTN" },
    { name: "Player 2", stack: 1000, position: "SB" }
  ],
  buttonPosition: "BTN",
  smallBlind: 5,
  bigBlind: 10
});
```

#### `recordAction`

Record player action.

```typescript
socket.emit('recordAction', {
  playerIdx: 0,
  action: "raise",
  amount: 30
});
```

#### `updateBoard`

Update community cards.

```typescript
socket.emit('updateBoard', {
  cards: ["As", "Kh", "Qd"],
  street: "flop"
});
```

#### `updateHoleCards`

Update player hole cards.

```typescript
socket.emit('updateHoleCards', {
  playerIdx: 0,
  cards: ["As", "Ad"]
});
```

### Server → Client

#### `connected`

Confirmation of connection.

```typescript
socket.on('connected', (data) => {
  console.log('Connected:', data.clientId);
});
```

#### `gameInitialized`

Game has been initialized.

```typescript
socket.on('gameInitialized', (gameState) => {
  console.log('Game started:', gameState.id);
});
```

#### `actionRecorded`

Action has been recorded.

```typescript
socket.on('actionRecorded', ({ action, gameState }) => {
  console.log('Action:', action);
});
```

#### `boardUpdated`

Board has been updated with equity and recommendations.

```typescript
socket.on('boardUpdated', ({ gameState, equity, recommendations }) => {
  console.log('Board:', gameState.board);
  console.log('Equity:', equity);
  console.log('Recommendations:', recommendations);
});
```

#### `error`

Error occurred.

```typescript
socket.on('error', (error) => {
  console.error('Error:', error.message);
});
```

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE"
  },
  "timestamp": "2026-01-14T..."
}
```

Common error codes:
- `NO_ACTIVE_GAME` - No game in progress
- `INVALID_PLAYER_INDEX` - Invalid player index
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

