import { Card as CardType } from '@tpb/shared';
import { formatCard } from '@tpb/shared';

interface CardProps {
  card: CardType;
  size?: 'sm' | 'md' | 'lg';
}

export function Card({ card, size = 'md' }: CardProps) {
  const sizeClasses = {
    sm: 'w-12 h-16 text-lg',
    md: 'w-16 h-24 text-2xl',
    lg: 'w-20 h-32 text-3xl',
  };

  const suit = card[1].toLowerCase();
  const isRed = suit === 'h' || suit === 'd';

  return (
    <div className={`card ${sizeClasses[size]} flex items-center justify-center font-bold ${
      isRed ? 'text-red-600' : 'text-black'
    }`}>
      {formatCard(card)}
    </div>
  );
}

