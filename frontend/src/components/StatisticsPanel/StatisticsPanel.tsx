import { GameState } from '@tpb/shared';
import styles from './StatisticsPanel.module.css';

interface StatisticsPanelProps {
  gameState: GameState;
}

export function StatisticsPanel({ gameState }: StatisticsPanelProps) {
  return (
    <div className={styles.panel}>
      <h2 className="text-xl font-bold text-white mb-4">Statistics</h2>
      
      <div className="space-y-4">
        {gameState.players.map((player, idx) => (
          <div key={idx} className="bg-gray-800 p-3 rounded-lg">
            <p className="text-white font-semibold">{player.name}</p>
            <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
              <div>
                <p className="text-gray-400">VPIP</p>
                <p className="text-white">{player.vpip?.toFixed(1) || '0.0'}%</p>
              </div>
              <div>
                <p className="text-gray-400">PFR</p>
                <p className="text-white">{player.pfr?.toFixed(1) || '0.0'}%</p>
              </div>
              <div>
                <p className="text-gray-400">AGG</p>
                <p className="text-white">{player.aggression?.toFixed(2) || '0.00'}</p>
              </div>
              <div>
                <p className="text-gray-400">Stack</p>
                <p className="text-poker-gold">${player.stack}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

