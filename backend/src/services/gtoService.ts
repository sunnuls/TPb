import { GameState, StrategyRecommendation, GTORecommendation, Position } from '@tpb/shared';
import { logger } from '../utils/logger';
import { getOpeningRange, get3BetRange, getColdCallRange } from '../data/gtoRanges';
import { RangeConstructorService } from './rangeConstructorService';

export class GTOService {
  private rangeService: RangeConstructorService;

  constructor() {
    this.rangeService = new RangeConstructorService();
  }

  /**
   * Get GTO-based strategy recommendations
   */
  async getRecommendations(gameState: GameState): Promise<StrategyRecommendation> {
    const startTime = Date.now();

    try {
      const currentPlayer = gameState.players[gameState.currentPlayerIdx];
      const position = currentPlayer.position;
      const street = gameState.street;

      // Preflop recommendations
      if (street === 'preflop') {
        return this.getPreflopRecommendations(gameState, position);
      }

      // Postflop recommendations (simplified)
      return this.getPostflopRecommendations(gameState, position);

    } catch (error) {
      logger.error(`GTO recommendation failed: ${error}`);
      throw error;
    } finally {
      const duration = Date.now() - startTime;
      logger.info(`GTO recommendation generated in ${duration}ms`);
    }
  }

  /**
   * Get preflop GTO recommendations
   */
  private getPreflopRecommendations(
    gameState: GameState,
    position: Position
  ): StrategyRecommendation {
    const actionHistory = this.getStreetActions(gameState, 'preflop');
    const hasRaise = actionHistory.some(a => a.action === 'raise');
    const has3Bet = actionHistory.filter(a => a.action === 'raise').length >= 2;

    // No action yet - opening range
    if (!hasRaise) {
      const openingRange = getOpeningRange(position);
      
      return {
        primary: {
          action: 'raise',
          frequency: 1.0,
          sizings: [2.5, 3.0], // 2.5-3x BB
          reasoning: `Open ${openingRange.description}`,
          evDifference: 0,
        },
        alternatives: [
          {
            action: 'fold',
            frequency: 0,
            reasoning: 'Fold hands outside opening range',
            evDifference: -0.5,
          },
        ],
      };
    }

    // Facing a raise - 3-bet or call/fold
    if (hasRaise && !has3Bet) {
      const raiser = actionHistory.find(a => a.action === 'raise');
      const raiserPosition = gameState.players[raiser!.playerIdx].position;
      
      const threeBetRange = get3BetRange(position, raiserPosition);
      const callRange = getColdCallRange(position, raiserPosition);

      return {
        primary: {
          action: 'call',
          frequency: callRange ? 0.65 : 0.5,
          reasoning: callRange ? callRange.description : 'Call with playable hands',
          evDifference: 0,
        },
        alternatives: [
          {
            action: 'raise',
            frequency: threeBetRange ? threeBetRange.frequency : 0.15,
            sizings: [3.0, 3.5], // 3x original raise
            reasoning: threeBetRange ? threeBetRange.description : '3-bet with premium hands',
            evDifference: -0.03,
          },
          {
            action: 'fold',
            frequency: 0.20,
            reasoning: 'Fold weak hands',
            evDifference: -0.2,
          },
        ],
      };
    }

    // Facing a 3-bet - 4-bet or call/fold
    if (has3Bet) {
      return {
        primary: {
          action: 'fold',
          frequency: 0.70,
          reasoning: 'Fold most of range vs 3-bet',
          evDifference: 0,
        },
        alternatives: [
          {
            action: 'call',
            frequency: 0.20,
            reasoning: 'Call with medium-strong hands',
            evDifference: -0.05,
          },
          {
            action: 'raise',
            frequency: 0.10,
            sizings: [2.2], // 2.2x 3-bet size
            reasoning: '4-bet with premium hands',
            evDifference: -0.08,
          },
        ],
      };
    }

    // Default
    return this.getDefaultRecommendations();
  }

  /**
   * Get postflop GTO recommendations (simplified)
   */
  private getPostflopRecommendations(
    gameState: GameState,
    position: Position
  ): StrategyRecommendation {
    const pot = gameState.pot;
    const street = gameState.street;

    // Check if in position or out of position
    const buttonIdx = gameState.players.findIndex(p => p.position === 'BTN');
    const currentIdx = gameState.currentPlayerIdx;
    const inPosition = currentIdx > buttonIdx || buttonIdx === currentIdx;

    // C-bet scenario (flop, was preflop raiser)
    if (street === 'flop') {
      return {
        primary: {
          action: 'bet',
          frequency: 0.70,
          sizings: [pot * 0.33, pot * 0.5, pot * 0.75],
          reasoning: 'C-bet with range advantage',
          evDifference: 0,
        },
        alternatives: [
          {
            action: 'check',
            frequency: 0.30,
            reasoning: 'Check with marginal hands and strong hands (trap)',
            evDifference: -0.05,
          },
        ],
      };
    }

    // Turn/River - more polarized
    return {
      primary: {
        action: 'check',
        frequency: 0.55,
        reasoning: `Check to ${inPosition ? 'control pot' : 'induce bluffs'}`,
        evDifference: 0,
      },
      alternatives: [
        {
          action: 'bet',
          frequency: 0.35,
          sizings: [pot * 0.66, pot * 1.0],
          reasoning: 'Bet for value or as bluff',
          evDifference: -0.03,
        },
        {
          action: 'fold',
          frequency: 0.10,
          reasoning: 'Fold weak hands facing aggression',
          evDifference: -0.15,
        },
      ],
    };
  }

  /**
   * Get default recommendations
   */
  private getDefaultRecommendations(): StrategyRecommendation {
    return {
      primary: {
        action: 'check',
        frequency: 0.65,
        reasoning: 'Default GTO mixed strategy',
        evDifference: 0,
      },
      alternatives: [
        {
          action: 'bet',
          frequency: 0.25,
          reasoning: 'Bet with strong hands',
          evDifference: -0.02,
        },
        {
          action: 'fold',
          frequency: 0.10,
          reasoning: 'Fold weak hands',
          evDifference: -0.15,
        },
      ],
    };
  }

  /**
   * Get actions for current street
   */
  private getStreetActions(gameState: GameState, street: string): any[] {
    // This would normally come from action history
    // For now, return empty array
    return [];
  }
}

