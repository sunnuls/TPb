import { Card, Equity } from '@tpb/shared';
import { EquityEngine } from '../engines/equityEngine';
import { logger } from '../utils/logger';

export class EquityService {
  private engine: EquityEngine;

  constructor() {
    this.engine = new EquityEngine({
      method: (process.env.EQUITY_METHOD as 'exact' | 'monte-carlo') || 'monte-carlo',
      maxIterations: parseInt(process.env.EQUITY_ITERATIONS || '100000'),
      precision: 4,
    });
  }

  async calculateEquity(hands: Card[][], board: Card[], dead: Card[] = []): Promise<Equity[]> {
    const startTime = Date.now();

    try {
      const equity = this.engine.calculateEquity(hands, board, dead);
      const duration = Date.now() - startTime;

      logger.info(`Equity calculated in ${duration}ms for ${hands.length} hands`);

      if (duration > 100) {
        logger.warn(`Equity calculation exceeded target latency: ${duration}ms`);
      }

      return equity;
    } catch (error) {
      logger.error(`Equity calculation failed: ${error}`);
      throw error;
    }
  }
}

