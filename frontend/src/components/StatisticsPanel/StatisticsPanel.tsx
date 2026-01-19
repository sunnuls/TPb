import { GameState } from '@tpb/shared';
import { RangeVisualizerGrid } from '../RangeVisualizer/RangeVisualizerGrid';
import styles from './StatisticsPanel.module.css';

interface StatisticsPanelProps {
  gameState: GameState;
}

export function StatisticsPanel({ gameState }: StatisticsPanelProps) {
  const getPlayerStyle = (vpip: number | undefined, pfr: number | undefined) => {
    if (!vpip || !pfr) return { style: 'Unknown', color: 'text-gray-400' };
    
    if (vpip < 15 && pfr < 12) return { style: 'Nit', color: 'text-blue-400' };
    if (vpip < 20 && pfr > 15) return { style: 'TAG', color: 'text-green-400' };
    if (vpip > 35 && pfr < 15) return { style: 'Fish', color: 'text-red-400' };
    if (vpip > 30 && pfr > 20) return { style: 'LAG', color: 'text-yellow-400' };
    return { style: 'Regular', color: 'text-white' };
  };

  return (
    <div className={styles.panel}>
      <h2 className="text-lg font-bold text-white mb-2">Statistics</h2>
      
      {/* Player Stats - Compact */}
      <div className="space-y-1.5 mb-3">
        {gameState.players.map((player, idx) => {
          const playerStyle = getPlayerStyle(player.vpip, player.pfr);
          return (
            <div key={idx} className={`bg-gray-800 p-1.5 rounded border-l-2 ${
              player.folded ? 'border-gray-600 opacity-50' : 'border-blue-500'
            }`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <p className="text-white font-semibold text-xs">{player.name}</p>
                  <span className={`text-[10px] ${playerStyle.color} font-bold`}>
                    {playerStyle.style}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <p className="text-yellow-400 font-bold text-xs">${player.stack}</p>
                  <p className="text-gray-400 text-[10px]">{player.position}</p>
                </div>
              </div>
              <div className="flex gap-2 text-[10px]">
                <span className="text-gray-400">V:{player.vpip?.toFixed(0) || '0'}%</span>
                <span className="text-gray-400">P:{player.pfr?.toFixed(0) || '0'}%</span>
                <span className="text-gray-400">A:{player.aggression?.toFixed(1) || '0'}</span>
                {player.bet > 0 && !player.folded && (
                  <span className="text-yellow-400 font-semibold ml-auto">Bet: ${player.bet}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Player Style Legend - Compact */}
      <div className="mb-3 p-1.5 bg-gray-800 rounded text-[10px]">
        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
          <span><span className="text-blue-400 font-bold">Nit</span> <span className="text-gray-500">tight</span></span>
          <span><span className="text-green-400 font-bold">TAG</span> <span className="text-gray-500">tight-agg</span></span>
          <span><span className="text-yellow-400 font-bold">LAG</span> <span className="text-gray-500">loose-agg</span></span>
          <span><span className="text-red-400 font-bold">Fish</span> <span className="text-gray-500">loose-pass</span></span>
        </div>
      </div>

      {/* Range Visualizer */}
      <div className="mt-2">
        <RangeVisualizerGrid position={gameState.buttonPosition} street={gameState.street} />
      </div>
    </div>
  );
}

