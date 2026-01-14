import { useState } from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import styles from './SettingsPanel.module.css';

export function SettingsPanel() {
  const {
    theme,
    notifications,
    soundEnabled,
    overlayOpacity,
    equityPrecision,
    autoConnect,
    setTheme,
    toggleNotifications,
    toggleSound,
    setOverlayOpacity,
    setEquityPrecision,
    toggleAutoConnect,
  } = useSettingsStore();

  return (
    <div className={styles.panel}>
      <h2 className="text-xl font-bold text-white mb-4">Settings</h2>

      <div className="space-y-6">
        {/* Theme */}
        <div>
          <label className="text-gray-300 text-sm font-semibold mb-2 block">
            Theme
          </label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as 'dark' | 'light' | 'auto')}
            className="w-full bg-gray-800 text-white px-3 py-2 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="auto">Auto</option>
          </select>
        </div>

        {/* Notifications */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-sm font-semibold">
            Enable Notifications
          </label>
          <button
            onClick={toggleNotifications}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              notifications ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                notifications ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Sound */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-sm font-semibold">
            Sound Effects
          </label>
          <button
            onClick={toggleSound}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              soundEnabled ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                soundEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Auto Connect */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-sm font-semibold">
            Auto Connect on Start
          </label>
          <button
            onClick={toggleAutoConnect}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              autoConnect ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoConnect ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Overlay Opacity */}
        <div>
          <label className="text-gray-300 text-sm font-semibold mb-2 block">
            Overlay Opacity: {overlayOpacity}%
          </label>
          <input
            type="range"
            min="10"
            max="100"
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        {/* Equity Precision */}
        <div>
          <label className="text-gray-300 text-sm font-semibold mb-2 block">
            Equity Precision (decimal places)
          </label>
          <input
            type="number"
            min="1"
            max="4"
            value={equityPrecision}
            onChange={(e) => setEquityPrecision(parseInt(e.target.value))}
            className="w-full bg-gray-800 text-white px-3 py-2 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Hotkeys Info */}
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <h3 className="text-white font-semibold mb-2">Keyboard Shortcuts</h3>
          <div className="space-y-1 text-sm text-gray-400">
            <div className="flex justify-between">
              <span>Toggle Overlay</span>
              <kbd className="px-2 py-1 bg-gray-900 rounded">Ctrl+H</kbd>
            </div>
            <div className="flex justify-between">
              <span>Toggle Stats</span>
              <kbd className="px-2 py-1 bg-gray-900 rounded">Ctrl+S</kbd>
            </div>
            <div className="flex justify-between">
              <span>Settings</span>
              <kbd className="px-2 py-1 bg-gray-900 rounded">Ctrl+,</kbd>
            </div>
          </div>
        </div>

        {/* Reset Button */}
        <button
          onClick={() => {
            if (confirm('Reset all settings to defaults?')) {
              setTheme('dark');
              setOverlayOpacity(90);
              setEquityPrecision(2);
            }
          }}
          className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}

