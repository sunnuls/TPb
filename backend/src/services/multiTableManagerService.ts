import { EventEmitter } from 'events';
import { GameState, Position } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface TableInfo {
  tableId: string;
  tableName: string;
  gameType: 'cash' | 'tournament' | 'sit_n_go';
  stakes: string;
  playerCount: number;
  heroSeat?: number;
  isActive: boolean;
  priority: number; // 1-10, higher = more important
  lastUpdate: Date;
}

export interface MultiTableState {
  tables: Map<string, GameState>;
  activeTableId?: string;
  totalTables: number;
  activeTables: number;
  focusMode: 'auto' | 'manual';
}

export interface TablePriority {
  tableId: string;
  priority: number;
  reason: string;
  urgency: 'low' | 'medium' | 'high' | 'urgent';
}

/**
 * Multi-Table Manager Service
 * Manages state across multiple poker tables simultaneously
 */
export class MultiTableManagerService extends EventEmitter {
  private tables: Map<string, GameState> = new Map();
  private tableInfo: Map<string, TableInfo> = new Map();
  private activeTableId?: string;
  private focusMode: 'auto' | 'manual' = 'auto';
  private maxTables: number = 8;

  /**
   * Add table to manager
   */
  addTable(tableId: string, info: Omit<TableInfo, 'tableId' | 'lastUpdate'>): void {
    logger.info(`Adding table: ${tableId}`);

    const tableInfo: TableInfo = {
      tableId,
      ...info,
      lastUpdate: new Date(),
    };

    this.tableInfo.set(tableId, tableInfo);

    // Initialize empty game state
    const gameState: GameState = {
      tableId,
      players: [],
      board: [],
      pot: 0,
      currentBet: 0,
      minimumRaise: 0,
      street: 'preflop',
      actions: [],
      heroIdx: info.heroSeat,
    };

    this.tables.set(tableId, gameState);

    // Auto-focus if this is the only table
    if (this.tables.size === 1) {
      this.setActiveTable(tableId);
    }

    this.emit('tableAdded', tableInfo);

    logger.info(`Table added: ${tableId}, total tables: ${this.tables.size}`);
  }

  /**
   * Remove table from manager
   */
  removeTable(tableId: string): void {
    const table = this.tableInfo.get(tableId);

    if (!table) {
      logger.warn(`Table not found: ${tableId}`);
      return;
    }

    this.tables.delete(tableId);
    this.tableInfo.delete(tableId);

    // If active table was removed, switch to next
    if (this.activeTableId === tableId) {
      this.switchToNextTable();
    }

    this.emit('tableRemoved', tableId);

    logger.info(`Table removed: ${tableId}, remaining: ${this.tables.size}`);
  }

  /**
   * Update game state for a table
   */
  updateTableState(tableId: string, state: Partial<GameState>): void {
    const existing = this.tables.get(tableId);

    if (!existing) {
      logger.warn(`Cannot update non-existent table: ${tableId}`);
      return;
    }

    const updated: GameState = {
      ...existing,
      ...state,
    };

    this.tables.set(tableId, updated);

    // Update table info
    const info = this.tableInfo.get(tableId);
    if (info) {
      info.lastUpdate = new Date();
      info.isActive = updated.players.some(p => p.isActive);
    }

    // Auto-focus if action required
    if (this.focusMode === 'auto' && this.requiresAction(updated)) {
      this.setActiveTable(tableId);
    }

    this.emit('tableStateUpdated', { tableId, state: updated });

    logger.debug(`Table state updated: ${tableId}`);
  }

  /**
   * Set active table
   */
  setActiveTable(tableId: string): void {
    if (!this.tables.has(tableId)) {
      logger.warn(`Cannot set active: table not found ${tableId}`);
      return;
    }

    this.activeTableId = tableId;
    this.emit('activeTableChanged', tableId);

    logger.info(`Active table set: ${tableId}`);
  }

  /**
   * Switch to next table (auto-rotation)
   */
  switchToNextTable(): void {
    if (this.tables.size === 0) {
      this.activeTableId = undefined;
      return;
    }

    // Get table priorities
    const priorities = this.calculateTablePriorities();

    if (priorities.length > 0) {
      // Switch to highest priority table
      this.setActiveTable(priorities[0].tableId);
    }
  }

  /**
   * Calculate priority for each table
   */
  calculateTablePriorities(): TablePriority[] {
    const priorities: TablePriority[] = [];

    for (const [tableId, state] of this.tables) {
      const info = this.tableInfo.get(tableId);
      if (!info || !info.isActive) continue;

      let priority = info.priority || 5;
      let reason = 'Normal priority';
      let urgency: TablePriority['urgency'] = 'medium';

      // Check if action required
      if (this.requiresAction(state)) {
        priority += 5;
        reason = 'Action required';
        urgency = 'urgent';
      }

      // Check if in big hand (large pot)
      if (state.pot > 50) {
        priority += 3;
        reason = 'Large pot';
        urgency = 'high';
      }

      // Check if all-in situation
      if (state.actions.some(a => a.action === 'all-in')) {
        priority += 4;
        reason = 'All-in situation';
        urgency = 'high';
      }

      // Tournament tables get higher priority
      if (info.gameType === 'tournament') {
        priority += 2;
      }

      priorities.push({
        tableId,
        priority,
        reason,
        urgency,
      });
    }

    // Sort by priority (descending)
    return priorities.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Check if table requires action from hero
   */
  private requiresAction(state: GameState): boolean {
    if (!state.heroIdx) return false;

    // Check if it's hero's turn (simplified)
    const activePlayers = state.players.filter(p => p.isActive);
    if (activePlayers.length === 0) return false;

    // In real implementation, check turn order
    return false; // Placeholder
  }

  /**
   * Get active table
   */
  getActiveTable(): GameState | undefined {
    if (!this.activeTableId) return undefined;
    return this.tables.get(this.activeTableId);
  }

  /**
   * Get table by ID
   */
  getTable(tableId: string): GameState | undefined {
    return this.tables.get(tableId);
  }

  /**
   * Get all tables
   */
  getAllTables(): GameState[] {
    return Array.from(this.tables.values());
  }

  /**
   * Get table info
   */
  getTableInfo(tableId: string): TableInfo | undefined {
    return this.tableInfo.get(tableId);
  }

  /**
   * Get all table info
   */
  getAllTableInfo(): TableInfo[] {
    return Array.from(this.tableInfo.values());
  }

  /**
   * Get active tables (with action)
   */
  getActiveTables(): GameState[] {
    return Array.from(this.tables.values()).filter((state) => {
      const info = this.tableInfo.get(state.tableId);
      return info?.isActive;
    });
  }

  /**
   * Set focus mode
   */
  setFocusMode(mode: 'auto' | 'manual'): void {
    this.focusMode = mode;
    logger.info(`Focus mode set to: ${mode}`);
  }

  /**
   * Get focus mode
   */
  getFocusMode(): 'auto' | 'manual' {
    return this.focusMode;
  }

  /**
   * Set max tables
   */
  setMaxTables(max: number): void {
    this.maxTables = Math.max(1, Math.min(16, max));
    logger.info(`Max tables set to: ${this.maxTables}`);
  }

  /**
   * Can add more tables
   */
  canAddTable(): boolean {
    return this.tables.size < this.maxTables;
  }

  /**
   * Get multi-table state
   */
  getState(): MultiTableState {
    return {
      tables: new Map(this.tables),
      activeTableId: this.activeTableId,
      totalTables: this.tables.size,
      activeTables: this.getActiveTables().length,
      focusMode: this.focusMode,
    };
  }

  /**
   * Clear all tables
   */
  clearAllTables(): void {
    this.tables.clear();
    this.tableInfo.clear();
    this.activeTableId = undefined;
    logger.info('All tables cleared');
  }
}

