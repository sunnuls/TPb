import { GameState } from '@tpb/shared';
import { EquityDisplay } from '../EquityDisplay/EquityDisplay';
import styles from './StrategyPanel.module.css';

interface StrategyPanelProps {
  gameState: GameState;
}

export function StrategyPanel({ gameState }: StrategyPanelProps) {
  const hero = gameState.players.find((p, idx) => idx === 0);
  const maxBet = Math.max(...gameState.players.map(p => p.bet));
  const toCall = hero ? maxBet - hero.bet : 0;

  return (
    <div className={styles.panel}>
      <h2 className="text-lg font-bold text-white mb-2">Strategy</h2>
      
      {/* Equity Calculator */}
      <EquityDisplay gameState={gameState} />

      {/* GTO Recommendations */}
      <div className="mt-3">
        <h3 className="text-sm font-semibold text-white mb-1.5">GTO Recommendations</h3>
        
        <div className="space-y-1.5">
          {/* CALL */}
          <button className="w-full bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 p-2 rounded-lg transition-all shadow-lg text-left">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-bold text-sm">✅ CALL</p>
                <p className="text-green-100 text-[10px]">Frequency: 65%</p>
              </div>
              <div className="text-right">
                <p className="text-white font-bold text-base">${toCall}</p>
                <p className="text-green-100 text-[9px]">to call</p>
              </div>
            </div>
            <p className="text-[9px] text-green-100 mt-1 opacity-90">
              GTO mixed strategy - flatting is optimal
            </p>
          </button>

          {/* RAISE */}
          <button className="w-full bg-gradient-to-r from-yellow-600 to-yellow-500 hover:from-yellow-700 hover:to-yellow-600 p-2 rounded-lg transition-all shadow-lg text-left">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-bold text-sm">📈 RAISE</p>
                <p className="text-yellow-100 text-[10px]">Frequency: 25%</p>
              </div>
              <div className="text-right">
                <p className="text-white font-bold text-base">${Math.round(toCall * 3)}</p>
                <p className="text-yellow-100 text-[9px]">suggested</p>
              </div>
            </div>
            <p className="text-[9px] text-yellow-100 mt-1 opacity-90">
              Polarized range (2.5x-3.0x) - value & bluffs
            </p>
          </button>

          {/* FOLD */}
          <button className="w-full bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 p-2 rounded-lg transition-all shadow-lg text-left">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-bold text-sm">❌ FOLD</p>
                <p className="text-red-100 text-[10px]">Frequency: 10%</p>
              </div>
              <div className="text-right">
                <p className="text-white font-bold text-base">$0</p>
                <p className="text-red-100 text-[9px]">save chips</p>
              </div>
            </div>
            <p className="text-[9px] text-red-100 mt-1 opacity-90">
              Weakest hands - preserve stack
            </p>
          </button>
        </div>
      </div>

      {/* Game Info */}
      <div className="mt-3 p-2 bg-blue-900 bg-opacity-30 rounded-lg border border-blue-700">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <p className="text-blue-300 text-[10px]">Street</p>
            <p className="text-white font-bold">{gameState.street.toUpperCase()}</p>
          </div>
          <div>
            <p className="text-blue-300 text-[10px]">Pot</p>
            <p className="text-poker-gold font-bold">${gameState.pot}</p>
          </div>
          <div>
            <p className="text-blue-300 text-[10px]">To Call</p>
            <p className="text-white font-bold">${toCall}</p>
          </div>
          <div>
            <p className="text-blue-300 text-[10px]">BB</p>
            <p className="text-white font-bold">{gameState.blinds.big}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

