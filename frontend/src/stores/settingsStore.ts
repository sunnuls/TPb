import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsStore {
  theme: 'dark' | 'light' | 'auto';
  notifications: boolean;
  soundEnabled: boolean;
  overlayOpacity: number;
  equityPrecision: number;
  autoConnect: boolean;
  
  setTheme: (theme: 'dark' | 'light' | 'auto') => void;
  toggleNotifications: () => void;
  toggleSound: () => void;
  setOverlayOpacity: (opacity: number) => void;
  setEquityPrecision: (precision: number) => void;
  toggleAutoConnect: () => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      theme: 'dark',
      notifications: true,
      soundEnabled: true,
      overlayOpacity: 90,
      equityPrecision: 2,
      autoConnect: true,
      
      setTheme: (theme) => set({ theme }),
      toggleNotifications: () => set((state) => ({ notifications: !state.notifications })),
      toggleSound: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
      setOverlayOpacity: (opacity) => set({ overlayOpacity: opacity }),
      setEquityPrecision: (precision) => set({ equityPrecision: precision }),
      toggleAutoConnect: () => set((state) => ({ autoConnect: !state.autoConnect })),
    }),
    {
      name: 'tpb-settings',
    }
  )
);

