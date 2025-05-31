import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Repository,
  EnrolledRepository,
  AuthStatus,
  SearchQuery,
  SearchResponse,
  SyncStatus,
  ConfigStatus,
  Dashboard,
  RepositoryEnrollmentForm,
  ApiResponse,
  ApiError,
} from '@/types/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_URL || '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for authentication
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('ff_docs_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Clear token and redirect to login
          localStorage.removeItem('ff_docs_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Helper method to handle API responses
  private handleResponse<T>(response: AxiosResponse<T>): T {
    return response.data;
  }

  private handleError(error: any): never {
    if (error.response?.data) {
      throw error.response.data as ApiError;
    }
    throw {
      detail: error.message || 'An unexpected error occurred',
      status_code: error.response?.status || 500,
    } as ApiError;
  }

  // Authentication endpoints
  async getAuthStatus(): Promise<AuthStatus> {
    try {
      const response = await this.client.get<AuthStatus>('/auth/status');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async login(token: string): Promise<AuthStatus> {
    try {
      localStorage.setItem('ff_docs_token', token);
      const response = await this.client.post<AuthStatus>('/auth/login');
      return this.handleResponse(response);
    } catch (error) {
      localStorage.removeItem('ff_docs_token');
      return this.handleError(error);
    }
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } catch (error) {
      // Continue with logout even if API call fails
    } finally {
      localStorage.removeItem('ff_docs_token');
    }
  }

  async getCurrentUser(): Promise<AuthStatus> {
    try {
      const response = await this.client.get<AuthStatus>('/auth/me');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Repository management endpoints
  async getRepositories(): Promise<Repository[]> {
    try {
      const response = await this.client.get<Repository[]>('/repos/discover');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getEnrolledRepositories(): Promise<EnrolledRepository[]> {
    try {
      const response = await this.client.get<EnrolledRepository[]>('/repos/');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async enrollRepository(data: RepositoryEnrollmentForm): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.post<ApiResponse<any>>('/repos/enroll', data);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async unenrollRepository(repositoryName: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.delete<ApiResponse<any>>(`/repos/unenroll`, {
        data: { repository: repositoryName },
      });
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async enrollAllRepositories(org: string, excludePrivate = true): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.post<ApiResponse<any>>('/repos/enroll-all', {
        org,
        exclude_private: excludePrivate,
      });
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Search endpoints
  async search(query: SearchQuery): Promise<SearchResponse> {
    try {
      const response = await this.client.post<SearchResponse>('/docs/search', query);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Sync and webhook endpoints
  async getSyncStatus(repository?: string): Promise<SyncStatus | Record<string, SyncStatus>> {
    try {
      const url = repository ? `/webhooks/sync/status/${repository}` : '/webhooks/sync/status';
      const response = await this.client.get<SyncStatus | Record<string, SyncStatus>>(url);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async triggerSync(repository: string, commitSha?: string): Promise<SyncStatus> {
    try {
      const response = await this.client.post<SyncStatus>('/webhooks/sync/trigger', {
        repository,
        commit_sha: commitSha,
      });
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async generateUnifiedConfig(): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.post<ApiResponse<any>>('/webhooks/build/unified-config');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Configuration endpoints
  async getConfigStatus(): Promise<ConfigStatus> {
    try {
      const response = await this.client.get<ConfigStatus>('/repos/config');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Health check
  async getHealth(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await this.client.get<{ status: string; timestamp: string }>('/health/');
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  // Dashboard data
  async getDashboard(): Promise<Dashboard> {
    try {
      // This endpoint might not exist yet, so we'll construct dashboard data
      // from other endpoints for now
      const [enrolledRepos, configStatus] = await Promise.all([
        this.getEnrolledRepositories(),
        this.getConfigStatus(),
      ]);

      return {
        total_repositories: configStatus.enrolled_repositories,
        accessible_repositories: enrolledRepos.length,
        recent_updates: enrolledRepos.slice(0, 5).map((repo) => ({
          repository: repo.name,
          updated_at: repo.last_sync || repo.enrolled_at,
          type: 'sync' as const,
          message: `Documentation updated for ${repo.name}`,
        })),
        search_stats: {
          total_searches: 0, // Placeholder
          popular_queries: [], // Placeholder
        },
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

export const apiService = new ApiService();
export default apiService;
