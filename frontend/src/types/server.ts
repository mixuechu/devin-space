import { Server } from '../types';

export interface APIClusterInfo {
  cluster_id: string;
  name: string;
  common_tags: string[];
}

export interface ClusterInfo {
  cluster_id: string;
  name: string;
  cluster_name: string;
  common_tags: string[];
  server_count: number;
}

export interface ClusterSummary {
  cluster_id: string;
  cluster_name: string;
  entity_name?: string;
  name?: string;
  common_tags: string[];
  server_count: number;
  avg_feature_count: number;
  avg_tool_count: number;
  avg_word_count: number;
}

export interface APIServer extends Omit<Server, 'cluster_info'> {
  cluster_info?: APIClusterInfo;
  cluster_id?: number;
  cluster_name?: string;
}

export interface ServerWithExtras extends Omit<Server, 'cluster_info'> {
  cluster_info?: ClusterInfo;
}

export interface ServersData {
  servers: ServerWithExtras[];
  total: number;
} 