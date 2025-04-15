import axios from 'axios';
import type { Server, VisualizationData, ClusterSummary, EvaluationSummary } from '../types';

const getBaseUrl = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // Remove any trailing slashes
  const cleanUrl = apiUrl.replace(/\/+$/, '');
  
  if (cleanUrl.startsWith('/')) {
    return cleanUrl;
  }
  
  try {
    new URL(cleanUrl);
    return cleanUrl;
  } catch (e) {
    console.error('Invalid API URL format:', e);
    return cleanUrl;
  }
};

export const API_URL = getBaseUrl();

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

export interface StatusResponse {
  status: string;
  server_count: number;
  has_clustering: boolean;
  has_evaluation: boolean;
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
  page: number;
  page_size: number;
}

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  tags: string[];
  relevance_score: number;
  quality_score?: number;
}

export interface ClusteringResponse {
  message: string;
  cluster_count: number;
  visualization_data: VisualizationData;
  cluster_summaries: ClusterSummary[];
}

export interface EvaluationResponse {
  message: string;
  evaluation_summary: EvaluationSummary;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface RecommendationResponse {
  query: string;
  recommendations: SearchResult[];
}

export interface PersonalizedRecommendationResponse {
  preferences: Record<string, any>;
  recommendations: SearchResult[];
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

export async function getServers(
  page: number = 1, 
  pageSize: number = 30, 
  clusterId?: string,
  searchTerm?: string
): Promise<GetServersResponse> {
  const queryParams = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  
  if (clusterId) {
    queryParams.append('cluster_id', clusterId);
  }

  if (searchTerm) {
    queryParams.append('search', searchTerm);
  }
  
  const response = await fetch(`${API_URL}/api/servers?${queryParams}`);
  if (!response.ok) {
    throw new Error('Failed to fetch servers');
  }
  return response.json();
}

export async function getServerDetails(serverId: string): Promise<Server> {
  const response = await fetch(`${API_URL}/api/servers/${serverId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch server details');
  }
  return response.json();
}

export async function clusterServers(similarityThreshold: number = 0.7): Promise<ClusteringResponse> {
  const response = await fetch(`${API_URL}/api/cluster`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ similarity_threshold: similarityThreshold }),
  });
  const data = await handleResponse<ClusteringResponse>(response);
  console.log('【API原始数据】Clustering API Response:', {
    cluster_count: data.cluster_count,
    cluster_summaries: data.cluster_summaries.map(summary => ({
      cluster_id: summary.cluster_id,
      cluster_name: summary.cluster_name,
      size: summary.size,
      servers: summary.servers.slice(0, 3),  // 只显示前3个服务器用于调试
      common_tags: summary.common_tags
    }))
  });
  return data;
}

export async function evaluateServers(): Promise<EvaluationResponse> {
  const response = await fetch(`${API_URL}/api/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return handleResponse<EvaluationResponse>(response);
}

export async function searchServers(query: string, topN: number = 5): Promise<SearchResponse> {
  const response = await fetch(`${API_URL}/search?query=${encodeURIComponent(query)}&top_n=${topN}`);
  return handleResponse<SearchResponse>(response);
}

export async function getRecommendations(query: string, topN: number = 3): Promise<RecommendationResponse> {
  const response = await fetch(`${API_URL}/recommend?query=${encodeURIComponent(query)}&top_n=${topN}`);
  return handleResponse<RecommendationResponse>(response);
}

export async function getPersonalizedRecommendations(
  preferences: Record<string, any>,
  topN: number = 3
): Promise<PersonalizedRecommendationResponse> {
  const response = await fetch(`${API_URL}/personalized-recommendations?top_n=${topN}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ preferences }),
  });
  return handleResponse<PersonalizedRecommendationResponse>(response);
}

export default api;
