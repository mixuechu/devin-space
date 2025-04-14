export interface Server {
  server_id: string;
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
    server_id: string;
    title: string;
    description: string;
    similarity_score?: number;
  }>;
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
  top_servers: Array<{
    id: string;
    title: string;
    score: number;
  }>;
  score_distribution: {
    excellent: number;
    good: number;
    average: number;
    below_average: number;
    poor: number;
  };
}

export interface ClusterSummary {
  cluster_id: number;
  size: number;
  servers: Array<{
    id: string;
    title: string;
  }>;
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