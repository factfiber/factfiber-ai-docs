// Re-export all types
export * from './api';

// Additional UI-specific types
export interface Theme {
  mode: 'light' | 'dark';
}

export interface AppState {
  user: import('./api').User | null;
  authenticated: boolean;
  theme: Theme;
  loading: boolean;
  error: string | null;
}

export interface RouteConfig {
  path: string;
  component: React.ComponentType;
  protected: boolean;
  exact?: boolean;
  title: string;
  description?: string;
}