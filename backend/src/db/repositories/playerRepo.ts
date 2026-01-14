import { query } from '../connection';
import { logger } from '../../utils/logger';

export class PlayerRepository {
  async getPlayerStats(playerName: string): Promise<any> {
    try {
      const result = await query(
        `SELECT * FROM player_stats WHERE player_name = $1`,
        [playerName]
      );

      return result.rows[0] || null;
    } catch (error) {
      logger.error(`Failed to get player stats: ${error}`);
      throw error;
    }
  }

  async updatePlayerStats(playerName: string, stats: any): Promise<void> {
    try {
      await query(
        `INSERT INTO player_stats (player_name, total_hands, hands_won, vpip, pfr, aggression, wtsd, won_at_showdown, total_winnings)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         ON CONFLICT (player_name)
         DO UPDATE SET
           total_hands = player_stats.total_hands + EXCLUDED.total_hands,
           hands_won = player_stats.hands_won + EXCLUDED.hands_won,
           vpip = EXCLUDED.vpip,
           pfr = EXCLUDED.pfr,
           aggression = EXCLUDED.aggression,
           wtsd = EXCLUDED.wtsd,
           won_at_showdown = EXCLUDED.won_at_showdown,
           total_winnings = player_stats.total_winnings + EXCLUDED.total_winnings,
           last_played_at = CURRENT_TIMESTAMP,
           updated_at = CURRENT_TIMESTAMP`,
        [
          playerName,
          stats.totalHands || 1,
          stats.handsWon || 0,
          stats.vpip || 0,
          stats.pfr || 0,
          stats.aggression || 0,
          stats.wtsd || 0,
          stats.wonAtShowdown || 0,
          stats.totalWinnings || 0,
        ]
      );

      logger.info(`Player stats updated for ${playerName}`);
    } catch (error) {
      logger.error(`Failed to update player stats: ${error}`);
      throw error;
    }
  }

  async createSession(playerName: string, buyIn: number): Promise<number> {
    try {
      const result = await query(
        `INSERT INTO sessions (player_name, buy_in)
         VALUES ($1, $2)
         RETURNING id`,
        [playerName, buyIn]
      );

      logger.info(`Session created for ${playerName}`);
      return result.rows[0].id;
    } catch (error) {
      logger.error(`Failed to create session: ${error}`);
      throw error;
    }
  }

  async endSession(sessionId: number, cashOut: number): Promise<void> {
    try {
      await query(
        `UPDATE sessions
         SET end_time = CURRENT_TIMESTAMP,
             cash_out = $1,
             net_result = $1 - buy_in,
             duration_minutes = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time)) / 60
         WHERE id = $2`,
        [cashOut, sessionId]
      );

      logger.info(`Session ${sessionId} ended`);
    } catch (error) {
      logger.error(`Failed to end session: ${error}`);
      throw error;
    }
  }
}

