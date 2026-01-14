import { useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { ServerToClientEvents, ClientToServerEvents } from '@tpb/shared';
import { useGameStore } from '../stores/gameStore';

type TypedSocket = Socket<ServerToClientEvents, ClientToServerEvents>;

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:3000';

export function useWebSocket() {
  const [socket, setSocket] = useState<TypedSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { setGameState, addAction } = useGameStore();

  const connect = useCallback(() => {
    const newSocket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    }) as TypedSocket;

    newSocket.on('connect', () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
    });

    newSocket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason);
      setIsConnected(false);
    });

    newSocket.on('connected', (data) => {
      console.log('📡 Server confirmed connection:', data.clientId);
    });

    newSocket.on('gameInitialized', (gameState) => {
      console.log('🎮 Game initialized:', gameState.id);
      setGameState(gameState);
    });

    newSocket.on('actionRecorded', ({ action, gameState }) => {
      console.log('🎯 Action recorded:', action);
      setGameState(gameState);
      addAction(action);
    });

    newSocket.on('boardUpdated', ({ gameState, equity, recommendations }) => {
      console.log('🃏 Board updated:', gameState.street);
      setGameState(gameState);
    });

    newSocket.on('error', (error) => {
      console.error('⚠️ Server error:', error);
    });

    newSocket.on('heartbeat', () => {
      // Silent heartbeat
    });

    setSocket(newSocket);
  }, [setGameState, addAction]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
  }, [socket]);

  return {
    socket,
    isConnected,
    connect,
    disconnect,
  };
}

