import { GameState, ApiResponse } from '@tpb/shared';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_URL;
  }

  /**
   * Generic fetch wrapper
   */
  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || 'API request failed');
      }

      return data;
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  /**
   * Get current game state
   */
  async getCurrentGame(): Promise<GameState | null> {
    const response = await this.fetch<GameState>('/api/game/current');
    return response.data || null;
  }

  /**
   * Get game history
   */
  async getGameHistory(): Promise<any[]> {
    const response = await this.fetch<any[]>('/api/game/history');
    return response.data || [];
  }

  /**
   * Get player statistics
   */
  async getPlayerStats(playerIdx: number): Promise<any> {
    const response = await this.fetch<any>(`/api/analytics/stats/${playerIdx}`);
    return response.data;
  }

  /**
   * Get all players statistics
   */
  async getAllPlayersStats(): Promise<any[]> {
    const response = await this.fetch<any[]>('/api/analytics/stats');
    return response.data || [];
  }

  /**
   * Calculate EV for actions
   */
  async calculateEV(data: any): Promise<any> {
    const response = await this.fetch<any>('/api/analytics/ev', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  /**
   * Build opponent range
   */
  async buildRange(data: any): Promise<any> {
    const response = await this.fetch<any>('/api/analytics/range', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  /**
   * Parse hand history
   */
  async parseHandHistory(text: string): Promise<any> {
    const response = await this.fetch<any>('/api/handhistory/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
    return response.data;
  }

  /**
   * Upload hand history file
   */
  async uploadHandHistory(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/api/handhistory/parse/file`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || 'Upload failed');
    }

    return data.data;
  }

  /**
   * Get health status
   */
  async getHealth(): Promise<any> {
    const response = await this.fetch<any>('/health');
    return response;
  }
}

export const apiService = new ApiService();

