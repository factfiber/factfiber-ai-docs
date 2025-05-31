// API Types for FactFiber Documentation Infrastructure

// Repository types
export interface Repository {
  name: string;
  description: string;
  url: string;
  docs_url?: string;
  has_docs: boolean;
  is_private: boolean;
  default_branch: string;
  stars: number;
  forks: number;
  language?: string;
  last_updated: string;
}

export interface EnrolledRepository {
  name: string;
  section: string;
  import_url: string;
  config: Record<string, any>;
  enrolled_at: string;
  last_sync?: string;
  sync_status?: 'pending' | 'syncing' | 'completed' | 'failed';
}

// User and authentication types
export interface User {
  username: string;
  email: string;
  avatar_url: string;
  name?: string;
  teams: string[];
  permissions: string[];
}

export interface AuthStatus {
  authenticated: boolean;
  user?: User;
  method: 'jwt' | 'oauth2-proxy' | null;
}

// Search types
export interface SearchQuery {
  query: string;
  repositories?: string[];
  sections?: string[];
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  title: string;
  url: string;
  content: string;
  repository: string;
  section?: string;
  score: number;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  filtered_results: number;
  repositories_searched: string[];
  execution_time_ms: number;
}

// Sync and webhook types
export interface SyncStatus {
  repository: string;
  commit_sha?: string;
  status: 'started' | 'cloning' | 'processing' | 'completed' | 'failed';
  message: string;
  docs_found: number;
  files_processed: number;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface WebhookResponse {
  status: 'processed' | 'ignored' | 'failed';
  message: string;
  repository?: string;
  commit_sha?: string;
  docs_updated: boolean;
}

// Configuration types
export interface ConfigStatus {
  github_configured: boolean;
  oauth2_proxy_configured: boolean;
  mkdocs_configured: boolean;
  temp_dir_writable: boolean;
  enrolled_repositories: number;
}

// API response wrappers
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface ApiError {
  detail: string;
  status_code: number;
  type?: string;
}

// Form types for UI
export interface RepositoryEnrollmentForm {
  repository: string;
  section: string;
  auto_sync: boolean;
}

export interface SearchForm {
  query: string;
  repositories: string[];
  sections: string[];
}

// Navigation and UI types
export interface NavigationItem {
  label: string;
  path: string;
  icon?: string;
  children?: NavigationItem[];
}

export interface Dashboard {
  total_repositories: number;
  accessible_repositories: number;
  recent_updates: Array<{
    repository: string;
    updated_at: string;
    type: 'sync' | 'enrollment' | 'config';
    message: string;
  }>;
  search_stats: {
    total_searches: number;
    popular_queries: Array<{
      query: string;
      count: number;
    }>;
  };
}
