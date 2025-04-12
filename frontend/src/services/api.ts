import axios from 'axios';

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

export interface Server {
  id: string;
  title: string;
  author: string;
  description: string;
  tags: string[];
  word_count: number;
  documentation_length: number;
  feature_count: number;
  tool_count: number;
  has_github: boolean;
  has_faq: boolean;
  cluster_id?: number;
  code_quality_score?: number;
  tool_completeness_score?: number;
  documentation_quality_score?: number;
  runtime_stability_score?: number;
  business_value_score?: number;
  overall_score?: number;
  raw_data?: Record<string, any>;
  similar_servers?: Array<{
    id: string;
    title: string;
    description: string;
    similarity_score?: number;
  }>;
}

export interface ClusterSummary {
  cluster_id: number;
  size: number;
  servers: { id: string; title: string }[];
  avg_word_count: number;
  avg_feature_count: number;
  avg_tool_count: number;
  common_tags: string[];
}

export interface VisualizationData {
  pca: { 
    x: number[]; 
    y: number[];
    clusters: number[];
    server_ids: string[];
    titles: string[];
  };
  tsne: { 
    x: number[]; 
    y: number[];
    clusters: number[];
    server_ids: string[];
    titles: string[];
  };
}

export interface EvaluationSummary {
  average_scores: {
    overall: number;
    code_quality: number;
    tool_completeness: number;
    documentation_quality: number;
    runtime_stability: number;
    business_value: number;
  };
  top_servers: { id: string; title: string; score: number }[];
  score_distribution: {
    excellent: number;
    good: number;
    average: number;
    below_average: number;
    poor: number;
  };
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

export const processData = async (dataPath: string) => {
  const response = await api.post('/process-data', null, {
    params: { data_path: dataPath },
  });
  return response.data;
};

export const getServers = async (params: {
  skip?: number;
  limit?: number;
  search?: string;
  cluster_id?: number;
}) => {
  const response = await api.get('/servers', { params });
  return response.data;
};

export const getServerDetails = async (serverId: string) => {
  const response = await api.get(`/servers/${serverId}`);
  return response.data;
};

export const clusterServers = async (similarityThreshold: number = 0.7) => {
  const response = await api.post('/cluster', null, {
    params: { similarity_threshold: similarityThreshold },
  });
  return response.data;
};

export const evaluateServers = async () => {
  const response = await api.post('/evaluate');
  return response.data;
};

export const searchServers = async (query: string, topN: number = 5) => {
  const response = await api.get('/search', {
    params: { query, top_n: topN },
  });
  return response.data;
};

export const recommendServers = async (query: string, topN: number = 3) => {
  const response = await api.get('/recommend', {
    params: { query, top_n: topN },
  });
  return response.data;
};

export const getPersonalizedRecommendations = async (
  userPreferences: UserPreferences,
  topN: number = 3
) => {
  const response = await api.post('/personalized-recommendations', userPreferences, {
    params: { top_n: topN },
  });
  return response.data;
};

export default api;
