import { Card as CardType } from '@tpb/shared';
import { formatCard } from '@tpb/shared';

interface CardProps {
  card: CardType;
  size?: 'sm' | 'md' | 'lg';
}

const suitSymbols: Record<string, string> = {
  's': '♠',
  'h': '♥',
  'd': '♦',
  'c': '♣'
};

const rankNames: Record<string, string> = {
  'A': 'A',
  'K': 'K',
  'Q': 'Q',
  'J': 'J',
  'T': '10',
  '9': '9',
  '8': '8',
  '7': '7',
  '6': '6',
  '5': '5',
  '4': '4',
  '3': '3',
  '2': '2'
};

export function Card({ card, size = 'md' }: CardProps) {
  const sizeClasses = {
    sm: 'w-14 h-20 text-base',
    md: 'w-20 h-28 text-2xl',
    lg: 'w-24 h-36 text-3xl',
  };

  const rank = card[0];
  const suit = card[1].toLowerCase();
  const isRed = suit === 'h' || suit === 'd';

  return (
    <div className={`
      ${sizeClasses[size]} 
      bg-white rounded-lg shadow-xl 
      flex flex-col items-center justify-between 
      p-2 border-2 border-gray-300
      transition-all hover:shadow-2xl
    `}>
      {/* Top rank/suit */}
      <div className={`font-bold leading-none ${
        isRed ? 'text-red-600' : 'text-gray-900'
      }`}>
        <div className="text-center">
          {rankNames[rank]}
        </div>
        <div className="text-center -mt-1">
          {suitSymbols[suit]}
        </div>
      </div>

      {/* Center suit symbol */}
      <div className={`${
        size === 'lg' ? 'text-5xl' : size === 'md' ? 'text-4xl' : 'text-2xl'
      } ${isRed ? 'text-red-600' : 'text-gray-900'}`}>
        {suitSymbols[suit]}
      </div>

      {/* Bottom rank/suit (upside down) */}
      <div className={`font-bold leading-none transform rotate-180 ${
        isRed ? 'text-red-600' : 'text-gray-900'
      }`}>
        <div className="text-center">
          {rankNames[rank]}
        </div>
        <div className="text-center -mt-1">
          {suitSymbols[suit]}
        </div>
      </div>
    </div>
  );
}

