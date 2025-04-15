import { VisualizationData, ClusterSummary, Server, EvaluationSummary } from '../types';

interface DataCache {
  clustering?: {
    visualization_data: VisualizationData;
    cluster_summaries: ClusterSummary[];
    timestamp?: number;
  };
  servers?: {
    servers: Server[];
    total: number;
    timestamp?: number;
  };
  evaluation?: EvaluationSummary & {
    timestamp?: number;
  };
}

const STORAGE_KEY = 'mcp_data_cache';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

class StaticDataManager {
  private static instance: StaticDataManager;
  private cache: DataCache = {};
  private initialized: boolean = false;

  private constructor() {
    this.loadFromStorage();
  }

  static getInstance(): StaticDataManager {
    if (!StaticDataManager.instance) {
      StaticDataManager.instance = new StaticDataManager();
    }
    return StaticDataManager.instance;
  }

  private loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedCache = JSON.parse(stored);
        // 验证缓存是否过期
        const now = Date.now();
        
        if (parsedCache.clustering && (!parsedCache.clustering.timestamp || now - parsedCache.clustering.timestamp > CACHE_DURATION)) {
          delete parsedCache.clustering;
        }
        
        if (parsedCache.servers && (!parsedCache.servers.timestamp || now - parsedCache.servers.timestamp > CACHE_DURATION)) {
          delete parsedCache.servers;
        }
        
        if (parsedCache.evaluation && (!parsedCache.evaluation.timestamp || now - parsedCache.evaluation.timestamp > CACHE_DURATION)) {
          delete parsedCache.evaluation;
        }

        this.cache = parsedCache;
        this.initialized = Object.keys(this.cache).length > 0;
      }
    } catch (error) {
      console.warn('Failed to load cache from localStorage:', error);
      this.clearAll();
    }
  }

  private saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.cache));
    } catch (error) {
      console.warn('Failed to save cache to localStorage:', error);
    }
  }

  // 集群数据缓存
  setClustering(data: { visualization_data: VisualizationData; cluster_summaries: ClusterSummary[] }) {
    this.cache.clustering = {
      ...data,
      timestamp: Date.now()
    };
    this.saveToStorage();
  }

  getClustering(): { visualization_data: VisualizationData; cluster_summaries: ClusterSummary[] } | null {
    return this.cache.clustering || null;
  }

  // 服务器列表缓存
  setServers(data: { servers: Server[]; total: number }) {
    this.cache.servers = {
      ...data,
      timestamp: Date.now()
    };
    this.saveToStorage();
  }

  getServers(): { servers: Server[]; total: number } | null {
    return this.cache.servers || null;
  }

  // 评估数据缓存
  setEvaluation(data: EvaluationSummary) {
    this.cache.evaluation = {
      ...data,
      timestamp: Date.now()
    };
    this.saveToStorage();
  }

  getEvaluation(): EvaluationSummary | null {
    return this.cache.evaluation || null;
  }

  // 检查是否已初始化
  isInitialized(): boolean {
    return this.initialized;
  }
  
  hasValidCache(): boolean {
    const now = Date.now();
    return Boolean(
      this.cache.servers?.timestamp && 
      now - this.cache.servers.timestamp <= CACHE_DURATION &&
      this.cache.evaluation?.timestamp &&
      now - this.cache.evaluation.timestamp <= CACHE_DURATION
    );
  }

  // 清除所有缓存（仅在开发时使用）
  clearAll() {
    this.cache = {};
    localStorage.removeItem(STORAGE_KEY);
    this.initialized = false;
  }
}

export const staticData = StaticDataManager.getInstance(); 