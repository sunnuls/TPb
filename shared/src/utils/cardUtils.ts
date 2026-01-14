import { Card, Rank, Suit } from '../types/poker';
import { RANKS, SUITS, RANK_VALUES, SUIT_SYMBOLS } from '../constants/cards';

export function parseCard(cardStr: string): { rank: Rank; suit: Suit } | null {
  if (cardStr.length !== 2) return null;
  
  const rank = cardStr[0].toUpperCase() as Rank;
  const suit = cardStr[1].toLowerCase() as Suit;
  
  if (!RANKS.includes(rank) || !SUITS.includes(suit)) {
    return null;
  }
  
  return { rank, suit };
}

export function formatCard(card: Card): string {
  const parsed = parseCard(card);
  if (!parsed) return card;
  
  return `${parsed.rank}${SUIT_SYMBOLS[parsed.suit]}`;
}

export function cardToIndex(card: Card): number {
  const parsed = parseCard(card);
  if (!parsed) return -1;
  
  const rankIdx = RANKS.indexOf(parsed.rank);
  const suitIdx = SUITS.indexOf(parsed.suit);
  
  return rankIdx * 4 + suitIdx;
}

export function indexToCard(index: number): Card | null {
  if (index < 0 || index >= 52) return null;
  
  const rankIdx = Math.floor(index / 4);
  const suitIdx = index % 4;
  
  return `${RANKS[rankIdx]}${SUITS[suitIdx]}` as Card;
}

export function cardsToMask(cards: Card[]): bigint {
  let mask = 0n;
  for (const card of cards) {
    const idx = cardToIndex(card);
    if (idx >= 0) {
      mask |= (1n << BigInt(idx));
    }
  }
  return mask;
}

export function maskToCards(mask: bigint): Card[] {
  const cards: Card[] = [];
  for (let i = 0; i < 52; i++) {
    if ((mask & (1n << BigInt(i))) !== 0n) {
      const card = indexToCard(i);
      if (card) cards.push(card);
    }
  }
  return cards;
}

export function sortCards(cards: Card[]): Card[] {
  return [...cards].sort((a, b) => {
    const parsedA = parseCard(a);
    const parsedB = parseCard(b);
    
    if (!parsedA || !parsedB) return 0;
    
    const rankDiff = RANK_VALUES[parsedA.rank] - RANK_VALUES[parsedB.rank];
    if (rankDiff !== 0) return -rankDiff; // Higher rank first
    
    return SUITS.indexOf(parsedA.suit) - SUITS.indexOf(parsedB.suit);
  });
}

export function areCardsEqual(card1: Card, card2: Card): boolean {
  return card1.toUpperCase() === card2.toUpperCase();
}

export function hasDuplicates(cards: Card[]): boolean {
  const seen = new Set<string>();
  for (const card of cards) {
    const normalized = card.toUpperCase();
    if (seen.has(normalized)) return true;
    seen.add(normalized);
  }
  return false;
}

