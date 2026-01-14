import { PlayerRepository } from '../db/repositories/playerRepo';
import { StatisticalAnalysisService } from './statisticalAnalysisService';
import { PlayerAction } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface AggregatedPlayerStats {
  playerName: string;
  totalHands: number;
  handsWon: number;
  winRate: number; // %
  vpip: number;
  pfr: number;
  aggression: number;
  wtsd: number;
  wonAtShowdown: number;
  totalWinnings: number;
  bigBlindsWon: number;
  lastPlayed: Date;
  sessions: number;
  averageSessionLength: number; // minutes
  bestSession: number;
  worstSession: number;
}

export class PlayerStatsAggregationService {
  private playerRepo: PlayerRepository;
  private statsService: StatisticalAnalysisService;

  constructor() {
    this.playerRepo = new PlayerRepository();
    this.statsService = new StatisticalAnalysisService();
  }

  /**
   * Aggregate player statistics from action history
   */
  async aggregatePlayerStats(
    playerName: string,
    actions: PlayerAction[]
  ): Promise<AggregatedPlayerStats> {
    logger.info(`Aggregating stats for player: ${playerName}`);

    // Get player index from actions
    const playerIdx = this.getPlayerIdx(playerName, actions);
    if (playerIdx === -1) {
      throw new Error(`Player ${playerName} not found in actions`);
    }

    // Calculate statistics
    const stats = this.statsService.calculatePlayerStats(playerIdx, actions);

    // Get existing stats from database
    const existingStats = await this.playerRepo.getPlayerStats(playerName);

    // Estimate hands won (simplified)
    const handsWon = Math.floor(stats.totalHands * (stats.vpip / 100) * 0.3);
    const winRate = stats.totalHands > 0 ? (handsWon / stats.totalHands) * 100 : 0;

    // Aggregate stats
    const aggregated: AggregatedPlayerStats = {
      playerName,
      totalHands: existingStats ? existingStats.total_hands + stats.totalHands : stats.totalHands,
      handsWon: existingStats ? existingStats.hands_won + handsWon : handsWon,
      winRate: Number(winRate.toFixed(2)),
      vpip: stats.vpip,
      pfr: stats.pfr,
      aggression: stats.aggression,
      wtsd: stats.wtsd,
      wonAtShowdown: stats.wonAtShowdown,
      totalWinnings: existingStats ? existingStats.total_winnings : 0,
      bigBlindsWon: 0,
      lastPlayed: new Date(),
      sessions: 1,
      averageSessionLength: 0,
      bestSession: 0,
      worstSession: 0,
    };

    // Save to database
    await this.playerRepo.updatePlayerStats(playerName, {
      totalHands: stats.totalHands,
      handsWon,
      vpip: stats.vpip,
      pfr: stats.pfr,
      aggression: stats.aggression,
      wtsd: stats.wtsd,
      wonAtShowdown: stats.wonAtShowdown,
      totalWinnings: 0,
    });

    logger.info(`Stats aggregated for ${playerName}: ${stats.totalHands} hands, ${stats.vpip}% VPIP`);

    return aggregated;
  }

  /**
   * Get leaderboard (top players by metric)
   */
  async getLeaderboard(
    metric: 'winRate' | 'totalHands' | 'vpip' | 'aggression',
    limit: number = 10
  ): Promise<AggregatedPlayerStats[]> {
    // This would query database for top players
    // For now, return empty array
    logger.info(`Getting leaderboard for ${metric}, limit ${limit}`);
    return [];
  }

  /**
   * Get player performance over time
   */
  async getPlayerTrend(
    playerName: string,
    days: number = 30
  ): Promise<Array<{ date: Date; vpip: number; pfr: number; winRate: number }>> {
    logger.info(`Getting trend for ${playerName} over ${days} days`);
    
    // This would query database for historical stats
    // For now, return empty array
    return [];
  }

  /**
   * Compare two players
   */
  async comparePlayers(
    player1: string,
    player2: string
  ): Promise<{
    player1Stats: AggregatedPlayerStats | null;
    player2Stats: AggregatedPlayerStats | null;
    comparison: {
      vpipDiff: number;
      pfrDiff: number;
      aggressionDiff: number;
      winRateDiff: number;
    };
  }> {
    const stats1 = await this.playerRepo.getPlayerStats(player1);
    const stats2 = await this.playerRepo.getPlayerStats(player2);

    if (!stats1 || !stats2) {
      return {
        player1Stats: null,
        player2Stats: null,
        comparison: {
          vpipDiff: 0,
          pfrDiff: 0,
          aggressionDiff: 0,
          winRateDiff: 0,
        },
      };
    }

    return {
      player1Stats: this.dbStatsToAggregated(player1, stats1),
      player2Stats: this.dbStatsToAggregated(player2, stats2),
      comparison: {
        vpipDiff: stats1.vpip - stats2.vpip,
        pfrDiff: stats1.pfr - stats2.pfr,
        aggressionDiff: stats1.aggression - stats2.aggression,
        winRateDiff: 0, // Calculate from data
      },
    };
  }

  /**
   * Get player index from name in actions
   */
  private getPlayerIdx(playerName: string, actions: PlayerAction[]): number {
    // In real implementation, this would map player names to indices
    // For now, return first player
    return actions.length > 0 ? actions[0].playerIdx : -1;
  }

  /**
   * Convert database stats to aggregated format
   */
  private dbStatsToAggregated(name: string, dbStats: any): AggregatedPlayerStats {
    return {
      playerName: name,
      totalHands: dbStats.total_hands || 0,
      handsWon: dbStats.hands_won || 0,
      winRate: dbStats.total_hands > 0 
        ? (dbStats.hands_won / dbStats.total_hands) * 100 
        : 0,
      vpip: dbStats.vpip || 0,
      pfr: dbStats.pfr || 0,
      aggression: dbStats.aggression || 0,
      wtsd: dbStats.wtsd || 0,
      wonAtShowdown: dbStats.won_at_showdown || 0,
      totalWinnings: dbStats.total_winnings || 0,
      bigBlindsWon: 0,
      lastPlayed: dbStats.last_played_at || new Date(),
      sessions: 1,
      averageSessionLength: 0,
      bestSession: 0,
      worstSession: 0,
    };
  }

  /**
   * Export player stats to CSV
   */
  exportToCSV(stats: AggregatedPlayerStats[]): string {
    const header = 'Name,Hands,Won,Win%,VPIP,PFR,Aggression,WTSD,Won@SD,Winnings\n';
    const rows = stats.map(s => 
      `${s.playerName},${s.totalHands},${s.handsWon},${s.winRate},${s.vpip},${s.pfr},${s.aggression},${s.wtsd},${s.wonAtShowdown},${s.totalWinnings}`
    ).join('\n');
    
    return header + rows;
  }
}

