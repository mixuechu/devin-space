import { Server } from '../types';

export interface ClusterInfo {
  cluster_id: string;
  name: string;
  common_tags: string[];
  server_count: number;
}

export interface ServerWithExtras extends Server {
  cluster_info?: ClusterInfo;
}

export interface ServersData {
  servers: ServerWithExtras[];
  total: number;
} 