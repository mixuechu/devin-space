import axios from 'axios';
import { Server, EvaluationSummary, ClusterSummary, VisualizationData } from '../types';

const getBaseUrl = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  
  if (apiUrl.startsWith('/')) {
    return apiUrl;
  }
  
  try {
    new URL(apiUrl);
    return apiUrl;
  } catch (e) {
    console.error('Invalid API URL format:', e);
    return apiUrl;
  }
};

const API_URL = getBaseUrl();

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false
});

if (!API_URL.startsWith('/')) {
  try {
    const url = new URL(API_URL);
    if (url.username && url.password) {
      api.defaults.headers.common['Authorization'] = 'Basic ' + btoa(`${url.username}:${url.password}`);
      
      const cleanUrl = new URL(url.toString());
      cleanUrl.username = '';
      cleanUrl.password = '';
      api.defaults.baseURL = cleanUrl.toString();
    }
  } catch (e) {
    console.error('Error extracting credentials from API URL:', e);
  }
} else {
  api.defaults.headers.common['Authorization'] = 'Basic ' + btoa('user:367eb335b64dc1a69dde4066af477585');
}

export interface GetServersParams {
  limit?: number;
  offset?: number;
  search?: string;
  cluster_id?: number;
}

export interface GetServersResponse {
  servers: Server[];
  total: number;
}

export interface StatusResponse {
  status: string;
  server_count: number;
  has_clustering: boolean;
  has_evaluation: boolean;
}

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  tags: string[];
  relevance_score: number;
  quality_score?: number;
  is_ai_recommendation?: boolean;
  personalized_score?: number;
  quality_scores?: {
    code_quality: number;
    tool_completeness: number;
    documentation_quality: number;
    runtime_stability: number;
    business_value: number;
  };
}

export interface UserPreferences {
  weights: {
    code_quality: number;
    tool_completeness: number;
    documentation_quality: number;
    runtime_stability: number;
    business_value: number;
  };
  preferred_tags: string[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 503) {
      throw new Error('Service unavailable: Data processing in progress');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getStatus(): Promise<StatusResponse> {
  const response = await fetch(`${API_URL}/status`);
  return handleResponse<StatusResponse>(response);
}

export async function getServers(params: GetServersParams = {}): Promise<GetServersResponse> {
  const queryParams = new URLSearchParams();
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.cluster_id !== undefined) queryParams.append('cluster_id', params.cluster_id.toString());
  
  const response = await fetch(`${API_URL}/servers?${queryParams}`);
  return handleResponse<GetServersResponse>(response);
}

export const getServerDetails = async (serverId: string): Promise<Server> => {
  const response = await fetch(`${API_URL}/servers/${serverId}`);
  return handleResponse<Server>(response);
};

export const clusterServers = async (similarityThreshold: number = 0.7): Promise<{
  message: string;
  cluster_count: number;
  visualization_data: VisualizationData;
  cluster_summaries: ClusterSummary[];
}> => {
  const response = await fetch(`${API_URL}/cluster`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ similarity_threshold: similarityThreshold })
  });
  return handleResponse<{
    message: string;
    cluster_count: number;
    visualization_data: VisualizationData;
    cluster_summaries: ClusterSummary[];
  }>(response);
};

export async function evaluateServers(): Promise<{ evaluation_summary: EvaluationSummary }> {
  const response = await fetch(`${API_URL}/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  });
  return handleResponse<{ evaluation_summary: EvaluationSummary }>(response);
}

export const searchServers = async (query: string, topN: number = 5): Promise<{
  query: string;
  results: SearchResult[];
}> => {
  const response = await fetch(`${API_URL}/search?query=${encodeURIComponent(query)}&top_n=${topN}`);
  return handleResponse<{ query: string; results: SearchResult[] }>(response);
};

export const recommendServers = async (query: string, topN: number = 3): Promise<{
  query: string;
  recommendations: SearchResult[];
}> => {
  const response = await fetch(`${API_URL}/recommend?query=${encodeURIComponent(query)}&top_n=${topN}`);
  return handleResponse<{ query: string; recommendations: SearchResult[] }>(response);
};

export const getPersonalizedRecommendations = async (
  userPreferences: UserPreferences,
  topN: number = 3
): Promise<{
  preferences: UserPreferences;
  recommendations: SearchResult[];
}> => {
  const response = await fetch(`${API_URL}/personalized-recommendations?top_n=${topN}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userPreferences),
  });
  return handleResponse<{ preferences: UserPreferences; recommendations: SearchResult[] }>(response);
};

export default api;
