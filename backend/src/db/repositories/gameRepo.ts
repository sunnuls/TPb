import { GameState } from '@tpb/shared';
import { query } from '../connection';
import { logger } from '../../utils/logger';

export class GameRepository {
  async createGame(gameState: GameState): Promise<void> {
    try {
      await query(
        `INSERT INTO games (id, button_position, small_blind, big_blind, ante, pot, street, status)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
        [
          gameState.id,
          gameState.buttonPosition,
          gameState.blinds.small,
          gameState.blinds.big,
          gameState.blinds.ante || null,
          gameState.pot,
          gameState.street,
          gameState.status,
        ]
      );

      // Insert players
      for (const player of gameState.players) {
        await query(
          `INSERT INTO players (game_id, player_idx, name, stack, position, folded, all_in, bet)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            gameState.id,
            player.idx,
            player.name,
            player.stack,
            player.position,
            player.folded,
            player.allIn,
            player.bet,
          ]
        );
      }

      logger.info(`Game ${gameState.id} saved to database`);
    } catch (error) {
      logger.error(`Failed to save game: ${error}`);
      throw error;
    }
  }

  async updateGame(gameState: GameState): Promise<void> {
    try {
      await query(
        `UPDATE games
         SET pot = $1, street = $2, status = $3, updated_at = CURRENT_TIMESTAMP
         WHERE id = $4`,
        [gameState.pot, gameState.street, gameState.status, gameState.id]
      );

      logger.info(`Game ${gameState.id} updated in database`);
    } catch (error) {
      logger.error(`Failed to update game: ${error}`);
      throw error;
    }
  }

  async getGame(gameId: string): Promise<any> {
    try {
      const result = await query(
        `SELECT * FROM games WHERE id = $1`,
        [gameId]
      );

      return result.rows[0] || null;
    } catch (error) {
      logger.error(`Failed to get game: ${error}`);
      throw error;
    }
  }

  async deleteGame(gameId: string): Promise<void> {
    try {
      await query(`DELETE FROM games WHERE id = $1`, [gameId]);
      logger.info(`Game ${gameId} deleted from database`);
    } catch (error) {
      logger.error(`Failed to delete game: ${error}`);
      throw error;
    }
  }
}

