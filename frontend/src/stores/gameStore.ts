import { create } from 'zustand';
import { GameState, PlayerAction } from '@tpb/shared';

interface GameStore {
  gameState: GameState | null;
  actionHistory: PlayerAction[];
  setGameState: (state: GameState) => void;
  addAction: (action: PlayerAction) => void;
  clearGame: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  gameState: null,
  actionHistory: [],
  setGameState: (state) => set({ gameState: state }),
  addAction: (action) => set((prev) => ({
    actionHistory: [...prev.actionHistory, action]
  })),
  clearGame: () => set({ gameState: null, actionHistory: [] }),
}));

