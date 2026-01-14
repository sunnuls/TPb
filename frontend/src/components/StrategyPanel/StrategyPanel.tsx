import { GameState } from '@tpb/shared';
import styles from './StrategyPanel.module.css';

interface StrategyPanelProps {
  gameState: GameState;
}

export function StrategyPanel({ gameState }: StrategyPanelProps) {
  return (
    <div className={styles.panel}>
      <h2 className="text-xl font-bold text-white mb-4">Strategy</h2>
      
      <div className="space-y-3">
        <div className="bg-gray-800 p-4 rounded-lg border-l-4 border-green-500">
          <p className="text-green-400 font-semibold mb-1">Recommended: Call</p>
          <p className="text-sm text-gray-400">Frequency: 65%</p>
          <p className="text-xs text-gray-500 mt-2">
            GTO mixed strategy for this spot
          </p>
        </div>

        <div className="bg-gray-800 p-4 rounded-lg border-l-4 border-yellow-500">
          <p className="text-yellow-400 font-semibold mb-1">Alternative: Raise</p>
          <p className="text-sm text-gray-400">Frequency: 25%</p>
          <p className="text-xs text-gray-500 mt-2">
            Polarized raising range (2.5x-3.0x)
          </p>
        </div>

        <div className="bg-gray-800 p-4 rounded-lg border-l-4 border-red-500">
          <p className="text-red-400 font-semibold mb-1">Fold</p>
          <p className="text-sm text-gray-400">Frequency: 10%</p>
          <p className="text-xs text-gray-500 mt-2">
            Weakest hands in range
          </p>
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-900 bg-opacity-30 rounded-lg">
        <p className="text-blue-300 text-sm">
          💡 Street: <strong>{gameState.street.toUpperCase()}</strong>
        </p>
        <p className="text-blue-300 text-sm mt-1">
          Pot: <strong>${gameState.pot}</strong>
        </p>
      </div>
    </div>
  );
}

