import React, { useState, useEffect } from 'react';
import { clusterServers } from '../services/api';
import { ClusterSummary } from '../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Loader2, RefreshCw } from 'lucide-react';
import { generateClusterNames } from '../utils/clusterUtils';
import { staticData } from '../store/dataCache';
import { Button } from './ui/button';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#A4DE6C'];

const ClusteringView: React.FC = () => {
  const [clusterSummaries, setClusterSummaries] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // 获取缓存的聚类数据
        const cachedData = staticData.getClustering();
        if (cachedData) {
          setClusterSummaries(cachedData.cluster_summaries);
          setLoading(false);
          return;
        }
        
        // 如果没有缓存数据，则获取新数据
        await fetchClusteringData();
      } catch (err) {
        console.error('Error initializing clustering data:', err);
        setError('Failed to initialize clustering data. Please try again later.');
        setLoading(false);
      }
    };

    initializeData();
  }, []);

  const fetchClusteringData = async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching clustering data from API...');
      
      const response = await clusterServers(0.7);
      
      if (response && response.cluster_summaries) {
        const namedClusters = generateClusterNames(response.cluster_summaries);
        
        // 保存到静态存储
        staticData.setClustering({
          visualization_data: response.visualization_data,
          cluster_summaries: namedClusters
        });
        
        setClusterSummaries(namedClusters);
      } else {
        throw new Error('Invalid response format from clustering API');
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching clustering data:', err);
      setError('Failed to fetch clustering data. Please try again later.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading cluster data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h2 className="text-2xl font-bold">Server Clustering Analysis</h2>
        
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchClusteringData(true)}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Recalculate Clusters
        </Button>
      </div>

      {error ? (
        <div className="bg-red-50 p-4 rounded-md text-red-800">
          <p>{error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clusterSummaries.length > 0 ? (
            clusterSummaries.map(cluster => (
              <Card key={cluster.cluster_id}>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: COLORS[cluster.cluster_id % COLORS.length] }}
                    ></div>
                    <CardTitle>{cluster.cluster_name}</CardTitle>
                  </div>
                  <CardDescription>
                    {cluster.size} servers with similar characteristics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm"><span className="font-medium">Avg. Features:</span> {cluster.avg_feature_count.toFixed(1)}</p>
                      <p className="text-sm"><span className="font-medium">Avg. Tools:</span> {cluster.avg_tool_count.toFixed(1)}</p>
                    </div>
                    
                    <div>
                      <p className="text-sm font-medium mb-1">Common Tags:</p>
                      <div className="flex flex-wrap gap-1">
                        {cluster.common_tags.map((tag: string, index: number) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {tag.replace(/^#\s*/, '')}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <p className="text-sm font-medium mb-1">Servers:</p>
                      <ul className="text-sm space-y-1">
                        {cluster.servers.slice(0, 5).map((server: { id: string; title: string }) => (
                          <li key={server.id} className="truncate">
                            {server.title}
                          </li>
                        ))}
                        {cluster.servers.length > 5 && (
                          <li className="text-muted-foreground">
                            +{cluster.servers.length - 5} more
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <div className="col-span-3 text-center py-8">
              <p className="text-muted-foreground">No cluster data available</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ClusteringView;
