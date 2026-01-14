import { PlayerAction, Street } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface PlayerStatistics {
  playerIdx: number;
  totalHands: number;
  vpip: number; // Voluntarily Put $ In Pot %
  pfr: number; // Pre-flop Raise %
  aggression: number; // (Bet + Raise) / Call ratio
  wtsd: number; // Went to showdown %
  wonAtShowdown: number; // Won at showdown %
  foldToFlop3Bet: number; // Fold to 3-bet on flop %
  foldToTurnBet: number; // Fold to turn bet %
  cbetFrequency: number; // Continuation bet frequency %
  checkRaiseFrequency: number; // Check-raise frequency %
}

export class StatisticalAnalysisService {
  /**
   * Calculate comprehensive statistics for a player from action history
   */
  calculatePlayerStats(playerIdx: number, actions: PlayerAction[]): PlayerStatistics {
    const playerActions = actions.filter(a => a.playerIdx === playerIdx);
    
    if (playerActions.length === 0) {
      return this.getEmptyStats(playerIdx);
    }

    // Group actions by street
    const actionsByStreet = this.groupActionsByStreet(playerActions);
    
    // Calculate each stat
    const totalHands = this.estimateTotalHands(actions);
    const vpip = this.calculateVPIP(playerActions, totalHands);
    const pfr = this.calculatePFR(playerActions, totalHands);
    const aggression = this.calculateAggression(playerActions);
    const wtsd = this.calculateWTSD(playerActions, totalHands);
    const wonAtShowdown = 0; // Placeholder - requires showdown data
    const foldToFlop3Bet = this.calculateFoldTo3Bet(playerActions, 'flop');
    const foldToTurnBet = this.calculateFoldToBet(playerActions, 'turn');
    const cbetFrequency = this.calculateCBetFrequency(playerActions);
    const checkRaiseFrequency = this.calculateCheckRaiseFrequency(playerActions);

    logger.info(`Stats calculated for player ${playerIdx}: VPIP=${vpip}%, PFR=${pfr}%`);

    return {
      playerIdx,
      totalHands,
      vpip,
      pfr,
      aggression,
      wtsd,
      wonAtShowdown,
      foldToFlop3Bet,
      foldToTurnBet,
      cbetFrequency,
      checkRaiseFrequency,
    };
  }

  /**
   * Calculate VPIP (Voluntarily Put $ In Pot)
   */
  private calculateVPIP(actions: PlayerAction[], totalHands: number): number {
    if (totalHands === 0) return 0;

    const preflopActions = actions.filter(a => a.street === 'preflop');
    const voluntaryActions = preflopActions.filter(
      a => ['call', 'raise', 'bet', 'all-in'].includes(a.action)
    );

    return Number(((voluntaryActions.length / totalHands) * 100).toFixed(2));
  }

  /**
   * Calculate PFR (Pre-flop Raise)
   */
  private calculatePFR(actions: PlayerAction[], totalHands: number): number {
    if (totalHands === 0) return 0;

    const preflopRaises = actions.filter(
      a => a.street === 'preflop' && ['raise', 'all-in'].includes(a.action)
    );

    return Number(((preflopRaises.length / totalHands) * 100).toFixed(2));
  }

  /**
   * Calculate Aggression Factor
   * Formula: (Bet + Raise) / Call
   */
  private calculateAggression(actions: PlayerAction[]): number {
    const aggressiveActions = actions.filter(a =>
      ['bet', 'raise', 'all-in'].includes(a.action)
    ).length;

    const passiveActions = actions.filter(a => a.action === 'call').length;

    if (passiveActions === 0) {
      return aggressiveActions > 0 ? 99.99 : 0;
    }

    return Number((aggressiveActions / passiveActions).toFixed(2));
  }

  /**
   * Calculate WTSD (Went to Showdown)
   */
  private calculateWTSD(actions: PlayerAction[], totalHands: number): number {
    if (totalHands === 0) return 0;

    // Estimate showdowns (river actions that aren't folds)
    const riverActions = actions.filter(a => a.street === 'river');
    const wentToShowdown = riverActions.filter(a => a.action !== 'fold').length;

    return Number(((wentToShowdown / totalHands) * 100).toFixed(2));
  }

  /**
   * Calculate fold to 3-bet frequency
   */
  private calculateFoldTo3Bet(actions: PlayerAction[], street: Street): number {
    const streetActions = actions.filter(a => a.street === street);
    
    // Look for fold after raise pattern
    let folds = 0;
    let opportunities = 0;

    for (let i = 1; i < streetActions.length; i++) {
      const prevAction = streetActions[i - 1];
      const currAction = streetActions[i];

      if (prevAction.action === 'raise') {
        opportunities++;
        if (currAction.action === 'fold') {
          folds++;
        }
      }
    }

    if (opportunities === 0) return 0;
    return Number(((folds / opportunities) * 100).toFixed(2));
  }

  /**
   * Calculate fold to bet frequency
   */
  private calculateFoldToBet(actions: PlayerAction[], street: Street): number {
    const streetActions = actions.filter(a => a.street === street);
    
    let folds = 0;
    let opportunities = 0;

    for (let i = 1; i < streetActions.length; i++) {
      const prevAction = streetActions[i - 1];
      const currAction = streetActions[i];

      if (prevAction.action === 'bet') {
        opportunities++;
        if (currAction.action === 'fold') {
          folds++;
        }
      }
    }

    if (opportunities === 0) return 0;
    return Number(((folds / opportunities) * 100).toFixed(2));
  }

  /**
   * Calculate continuation bet frequency
   */
  private calculateCBetFrequency(actions: PlayerAction[]): number {
    const preflopRaises = actions.filter(
      a => a.street === 'preflop' && ['raise', 'all-in'].includes(a.action)
    ).length;

    if (preflopRaises === 0) return 0;

    const flopBets = actions.filter(
      a => a.street === 'flop' && ['bet', 'all-in'].includes(a.action)
    ).length;

    return Number(((flopBets / preflopRaises) * 100).toFixed(2));
  }

  /**
   * Calculate check-raise frequency
   */
  private calculateCheckRaiseFrequency(actions: PlayerAction[]): number {
    let checkRaises = 0;
    let checks = 0;

    for (let i = 1; i < actions.length; i++) {
      const prevAction = actions[i - 1];
      const currAction = actions[i];

      if (
        prevAction.action === 'check' &&
        prevAction.playerIdx === currAction.playerIdx &&
        currAction.action === 'raise'
      ) {
        checkRaises++;
      }

      if (prevAction.action === 'check') {
        checks++;
      }
    }

    if (checks === 0) return 0;
    return Number(((checkRaises / checks) * 100).toFixed(2));
  }

  /**
   * Group actions by street
   */
  private groupActionsByStreet(actions: PlayerAction[]): Map<Street, PlayerAction[]> {
    const grouped = new Map<Street, PlayerAction[]>();

    for (const action of actions) {
      if (!grouped.has(action.street)) {
        grouped.set(action.street, []);
      }
      grouped.get(action.street)!.push(action);
    }

    return grouped;
  }

  /**
   * Estimate total hands (rough approximation)
   */
  private estimateTotalHands(actions: PlayerAction[]): number {
    // Count unique game identifiers or estimate from action count
    // For now, use simple heuristic: preflop actions / avg actions per hand
    const preflopActions = actions.filter(a => a.street === 'preflop').length;
    return Math.max(1, Math.floor(preflopActions / 3)); // Avg 3 preflop actions per hand
  }

  /**
   * Get empty stats for a player with no actions
   */
  private getEmptyStats(playerIdx: number): PlayerStatistics {
    return {
      playerIdx,
      totalHands: 0,
      vpip: 0,
      pfr: 0,
      aggression: 0,
      wtsd: 0,
      wonAtShowdown: 0,
      foldToFlop3Bet: 0,
      foldToTurnBet: 0,
      cbetFrequency: 0,
      checkRaiseFrequency: 0,
    };
  }

  /**
   * Get comparative analysis (player vs table average)
   */
  calculateComparativeStats(
    playerStats: PlayerStatistics,
    allPlayersStats: PlayerStatistics[]
  ): {
    vpipDiff: number;
    pfrDiff: number;
    aggressionDiff: number;
    tendency: 'tight-passive' | 'tight-aggressive' | 'loose-passive' | 'loose-aggressive' | 'balanced';
  } {
    const avgVPIP = allPlayersStats.reduce((sum, s) => sum + s.vpip, 0) / allPlayersStats.length;
    const avgPFR = allPlayersStats.reduce((sum, s) => sum + s.pfr, 0) / allPlayersStats.length;
    const avgAggression = allPlayersStats.reduce((sum, s) => sum + s.aggression, 0) / allPlayersStats.length;

    const vpipDiff = playerStats.vpip - avgVPIP;
    const pfrDiff = playerStats.pfr - avgPFR;
    const aggressionDiff = playerStats.aggression - avgAggression;

    // Classify tendency
    let tendency: 'tight-passive' | 'tight-aggressive' | 'loose-passive' | 'loose-aggressive' | 'balanced';

    if (Math.abs(vpipDiff) < 5 && Math.abs(aggressionDiff) < 0.5) {
      tendency = 'balanced';
    } else if (playerStats.vpip < 20) {
      tendency = playerStats.aggression > 2 ? 'tight-aggressive' : 'tight-passive';
    } else {
      tendency = playerStats.aggression > 2 ? 'loose-aggressive' : 'loose-passive';
    }

    return {
      vpipDiff: Number(vpipDiff.toFixed(2)),
      pfrDiff: Number(pfrDiff.toFixed(2)),
      aggressionDiff: Number(aggressionDiff.toFixed(2)),
      tendency,
    };
  }
}

