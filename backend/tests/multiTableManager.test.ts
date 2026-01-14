import { MultiTableManagerService } from '../src/services/multiTableManagerService';

describe('MultiTableManagerService', () => {
  let manager: MultiTableManagerService;

  beforeEach(() => {
    manager = new MultiTableManagerService();
  });

  describe('addTable', () => {
    it('should add table successfully', () => {
      manager.addTable('table1', {
        tableName: 'Test Table',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      const table = manager.getTable('table1');
      expect(table).toBeDefined();
      expect(table!.tableId).toBe('table1');
    });

    it('should set first table as active', () => {
      manager.addTable('table1', {
        tableName: 'Test Table',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      const state = manager.getState();
      expect(state.activeTableId).toBe('table1');
    });

    it('should emit tableAdded event', (done) => {
      manager.on('tableAdded', (info) => {
        expect(info.tableId).toBe('table1');
        done();
      });

      manager.addTable('table1', {
        tableName: 'Test',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });
    });
  });

  describe('removeTable', () => {
    it('should remove table successfully', () => {
      manager.addTable('table1', {
        tableName: 'Test',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      manager.removeTable('table1');

      const table = manager.getTable('table1');
      expect(table).toBeUndefined();
    });

    it('should switch to next table when active is removed', () => {
      manager.addTable('table1', {
        tableName: 'Table 1',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      manager.addTable('table2', {
        tableName: 'Table 2',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      expect(manager.getState().activeTableId).toBe('table1');

      manager.removeTable('table1');

      expect(manager.getState().activeTableId).toBe('table2');
    });
  });

  describe('updateTableState', () => {
    beforeEach(() => {
      manager.addTable('table1', {
        tableName: 'Test',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });
    });

    it('should update table state', () => {
      manager.updateTableState('table1', {
        pot: 100,
        board: ['As', 'Kh', 'Qd'],
      });

      const table = manager.getTable('table1');
      expect(table!.pot).toBe(100);
      expect(table!.board).toEqual(['As', 'Kh', 'Qd']);
    });

    it('should emit tableStateUpdated event', (done) => {
      manager.on('tableStateUpdated', ({ tableId, state }) => {
        expect(tableId).toBe('table1');
        expect(state.pot).toBe(150);
        done();
      });

      manager.updateTableState('table1', { pot: 150 });
    });
  });

  describe('calculateTablePriorities', () => {
    beforeEach(() => {
      manager.addTable('table1', {
        tableName: 'Normal Table',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      manager.addTable('table2', {
        tableName: 'Tournament',
        gameType: 'tournament',
        stakes: '$100',
        playerCount: 9,
        isActive: true,
        priority: 5,
      });
    });

    it('should calculate priorities', () => {
      const priorities = manager.calculateTablePriorities();

      expect(priorities.length).toBeGreaterThan(0);
      expect(priorities[0]).toHaveProperty('tableId');
      expect(priorities[0]).toHaveProperty('priority');
      expect(priorities[0]).toHaveProperty('reason');
    });

    it('should give tournament higher priority', () => {
      const priorities = manager.calculateTablePriorities();

      const tournamentPriority = priorities.find(p => p.tableId === 'table2');
      const cashPriority = priorities.find(p => p.tableId === 'table1');

      expect(tournamentPriority!.priority).toBeGreaterThan(cashPriority!.priority);
    });

    it('should sort by priority descending', () => {
      const priorities = manager.calculateTablePriorities();

      for (let i = 0; i < priorities.length - 1; i++) {
        expect(priorities[i].priority).toBeGreaterThanOrEqual(priorities[i + 1].priority);
      }
    });
  });

  describe('focus mode', () => {
    it('should default to auto mode', () => {
      expect(manager.getFocusMode()).toBe('auto');
    });

    it('should switch to manual mode', () => {
      manager.setFocusMode('manual');
      expect(manager.getFocusMode()).toBe('manual');
    });
  });

  describe('max tables', () => {
    it('should respect max tables limit', () => {
      manager.setMaxTables(2);

      manager.addTable('table1', {
        tableName: 'Table 1',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      manager.addTable('table2', {
        tableName: 'Table 2',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      expect(manager.canAddTable()).toBe(false);
    });

    it('should allow adding when under limit', () => {
      manager.setMaxTables(5);

      manager.addTable('table1', {
        tableName: 'Table 1',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      expect(manager.canAddTable()).toBe(true);
    });
  });

  describe('getState', () => {
    it('should return current multi-table state', () => {
      manager.addTable('table1', {
        tableName: 'Test',
        gameType: 'cash',
        stakes: '1/2',
        playerCount: 6,
        isActive: true,
        priority: 5,
      });

      const state = manager.getState();

      expect(state.totalTables).toBe(1);
      expect(state.activeTables).toBeGreaterThanOrEqual(0);
      expect(state.focusMode).toBe('auto');
      expect(state.activeTableId).toBe('table1');
    });
  });
});

