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
      <div className="min-h-screen bg-gray-900">
        {isConnected ? (
          <Overlay />
        ) : (
          <div className="flex items-center justify-center min-h-screen">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-white mx-auto mb-4"></div>
              <p className="text-white text-xl">Connecting to server...</p>
            </div>
          </div>
        )}
      </div>
    </ThemeProvider>
  );
}

export default App;

