# GTO Engine Documentation

## Overview

The GTO (Game Theory Optimal) Engine provides balanced, unexploitable strategy recommendations for poker decision-making.

## Features

### Preflop Ranges

The engine includes comprehensive preflop ranges for all positions:

#### Opening Ranges (RFI)
- **UTG**: ~12% (tight range)
- **MP**: ~17%
- **HJ**: ~22%
- **CO**: ~28%
- **BTN**: ~48% (widest range)
- **SB**: ~40%
- **BB**: ~52% (defense vs SB)

#### 3-Bet Ranges
Position-aware 3-betting frequencies:
- BTN vs CO: ~11%
- BTN vs HJ: ~9%
- SB vs BTN: ~12%
- BB vs BTN: ~14%
- BB vs SB: ~15%

#### 4-Bet Ranges
Polarized 4-betting strategies for premium hands and bluffs.

## Range Notation

The engine supports standard poker range notation:

- `AA` - Pocket aces
- `22+` - All pocket pairs from deuces up
- `AKs` - Ace-king suited
- `AKo` - Ace-king offsuit
- `A2s+` - All suited aces
- `KQs-K9s` - Suited kings from Q down to 9

## API Usage

### Get Opening Range

```typescript
import { getOpeningRange } from './data/gtoRanges';

const btnRange = getOpeningRange('BTN');
console.log(btnRange.range); // "22+,A2s+,K2s+,..."
console.log(btnRange.frequency); // 1.0
```

### Get 3-Bet Range

```typescript
import { get3BetRange } from './data/gtoRanges';

const threeBet = get3BetRange('BTN', 'CO');
console.log(threeBet.frequency); // 0.11 (11%)
console.log(threeBet.range); // "QQ+,AKs,AKo,..."
```

### Get Strategy Recommendation

```typescript
import { GTOService } from './services/gtoService';

const gtoService = new GTOService();
const recommendation = await gtoService.getRecommendations(gameState);

console.log(recommendation.primary.action); // "raise"
console.log(recommendation.primary.frequency); // 0.70
console.log(recommendation.alternatives); // Array of alternative actions
```

## Strategy Output

Recommendations include:

- **Primary Action**: Most frequent/optimal play
- **Alternatives**: Mixed strategy alternatives
- **Frequencies**: How often to take each action (0-1)
- **Sizings**: Recommended bet/raise sizes
- **Reasoning**: Explanation for the recommendation
- **EV Difference**: Cost of deviating from optimal play

## Integration

### Backend

```typescript
// In gameStateService or WebSocket handler
const gtoService = new GTOService();
const recommendations = await gtoService.getRecommendations(gameState);

socket.emit('boardUpdated', {
  gameState,
  equity,
  recommendations,
});
```

### Frontend

```typescript
// In StrategyPanel component
const { recommendations } = useGameState();

<div>
  <h3>Recommended: {recommendations.primary.action}</h3>
  <p>Frequency: {recommendations.primary.frequency * 100}%</p>
  <p>{recommendations.primary.reasoning}</p>
</div>
```

## Limitations

Current implementation uses simplified GTO approximations:

1. **Preflop**: Based on modern solver results but simplified
2. **Postflop**: Uses heuristics (not full solver solutions)
3. **Board Texture**: Not yet analyzed
4. **Stack Depths**: Simplified (needs M-ratio integration)
5. **Opponent Modeling**: Not yet implemented

## Future Enhancements

1. **Solver Integration**
   - PioSOLVER API
   - GTO+ integration
   - Custom solver results

2. **Board Texture Analysis**
   - Wet/dry boards
   - Connected/disconnected
   - High/low card dominance

3. **Stack Depth Adjustments**
   - Short stack (< 30bb)
   - Medium stack (30-100bb)
   - Deep stack (100bb+)

4. **Exploitative Adjustments**
   - Player tendency adaptation
   - Range narrowing based on history
   - Dynamic strategy shifts

## Performance

| Operation | Target | Actual |
|-----------|--------|--------|
| Range Lookup | < 10ms | ~1ms |
| Recommendation | < 50ms | ~10ms |

## References

- Modern Poker Theory (Michael Acevedo)
- Applications of No-Limit Hold'em (Matthew Janda)
- Play Optimal Poker (Andrew Brokos)

## Support

For GTO-related questions or custom range requests:
- Open an issue on GitHub
- Consult ROADMAP.md for future plans

