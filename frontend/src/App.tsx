import { useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { Overlay } from './components/Overlay/Overlay';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { connect, disconnect, isConnected } = useWebSocket();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gray-900 text-white">
        <div className="p-8">
          <h1 className="text-4xl font-bold mb-4">TPb - Poker Assistant</h1>
          <p className="text-xl mb-4">
            Status: {isConnected ? '🟢 Connected' : '🔴 Connecting...'}
          </p>
          
          {isConnected ? (
            <Overlay />
          ) : (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="text-center">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-white mx-auto mb-4"></div>
                <p className="text-white text-xl">Connecting to server...</p>
                <p className="text-gray-400 mt-2">Backend: http://localhost:3000</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App;

