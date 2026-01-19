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
      <h2 className="text-lg font-bold text-white mb-2">Settings</h2>

      <div className="space-y-3">
        {/* Theme */}
        <div>
          <label className="text-gray-300 text-xs font-semibold mb-1 block">
            Theme
          </label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as 'dark' | 'light' | 'auto')}
            className="w-full bg-gray-800 text-white px-2 py-1 rounded text-xs border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="auto">Auto</option>
          </select>
        </div>

        {/* Notifications */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-xs font-semibold">
            Enable Notifications
          </label>
          <button
            onClick={toggleNotifications}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              notifications ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                notifications ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Sound */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-xs font-semibold">
            Sound Effects
          </label>
          <button
            onClick={toggleSound}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              soundEnabled ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                soundEnabled ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Auto Connect */}
        <div className="flex items-center justify-between">
          <label className="text-gray-300 text-xs font-semibold">
            Auto Connect on Start
          </label>
          <button
            onClick={toggleAutoConnect}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              autoConnect ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                autoConnect ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Overlay Opacity */}
        <div>
          <label className="text-gray-300 text-xs font-semibold mb-1 block">
            Overlay Opacity: {overlayOpacity}%
          </label>
          <input
            type="range"
            min="10"
            max="100"
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseInt(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        {/* Equity Precision */}
        <div>
          <label className="text-gray-300 text-xs font-semibold mb-1 block">
            Equity Precision
          </label>
          <input
            type="number"
            min="1"
            max="4"
            value={equityPrecision}
            onChange={(e) => setEquityPrecision(parseInt(e.target.value))}
            className="w-full bg-gray-800 text-white px-2 py-1 rounded text-xs border border-gray-700 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Hotkeys Info */}
        <div className="bg-gray-800 p-2 rounded border border-gray-700">
          <h3 className="text-white font-semibold text-xs mb-1">Keyboard Shortcuts</h3>
          <div className="space-y-0.5 text-[10px] text-gray-400">
            <div className="flex justify-between">
              <span>Toggle Overlay</span>
              <kbd className="px-1 py-0.5 bg-gray-900 rounded text-[9px]">Ctrl+Q</kbd>
            </div>
            <div className="flex justify-between">
              <span>Toggle Stats</span>
              <kbd className="px-1 py-0.5 bg-gray-900 rounded text-[9px]">Ctrl+S</kbd>
            </div>
            <div className="flex justify-between">
              <span>Settings</span>
              <kbd className="px-1 py-0.5 bg-gray-900 rounded text-[9px]">Ctrl+,</kbd>
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
          className="w-full bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded text-xs transition-colors"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}

