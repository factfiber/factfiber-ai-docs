import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, AuthStatus } from '@/types/api';
import { apiService } from '@/services/api';

interface AuthContextType {
  user: User | null;
  authenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const authStatus: AuthStatus = await apiService.getAuthStatus();

      if (authStatus.authenticated && authStatus.user) {
        setUser(authStatus.user);
        setAuthenticated(true);
      } else {
        setUser(null);
        setAuthenticated(false);
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to check authentication status');
      setUser(null);
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (token: string) => {
    try {
      setLoading(true);
      setError(null);
      const authStatus: AuthStatus = await apiService.login(token);

      if (authStatus.authenticated && authStatus.user) {
        setUser(authStatus.user);
        setAuthenticated(true);
      } else {
        throw new Error('Login failed');
      }
    } catch (err: any) {
      setError(err.detail || 'Login failed');
      setUser(null);
      setAuthenticated(false);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await apiService.logout();
    } catch (err: any) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', err);
    } finally {
      setUser(null);
      setAuthenticated(false);
      setError(null);
      setLoading(false);
    }
  };

  const refreshAuth = async () => {
    await checkAuthStatus();
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const value: AuthContextType = {
    user,
    authenticated,
    loading,
    error,
    login,
    logout,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
