import React, { useState, useEffect } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts';
import { VisualizationData, ClusterSummary, clusterServers } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Loader2 } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#A4DE6C'];

const ClusteringView: React.FC = () => {
  const [visualizationData, setVisualizationData] = useState<VisualizationData | null>(null);
  const [clusterSummaries, setClusterSummaries] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [visualizationType, setVisualizationType] = useState<'pca' | 'tsne'>('tsne');

  useEffect(() => {
    fetchClusteringData();
  }, []);

  const fetchClusteringData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching entity linking data from API...');
      
      const response = await clusterServers(0.7);
      
      if (response && response.visualization_data && response.cluster_summaries) {
        setVisualizationData(response.visualization_data);
        setClusterSummaries(response.cluster_summaries);
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

  const prepareScatterData = () => {
    if (!visualizationData) return [];
    
    const { x, y, clusters, server_ids, titles } = visualizationData[visualizationType];
    
    return x.map((xVal, index) => ({
      x: xVal,
      y: y[index],
      cluster: clusters[index],
      id: server_ids[index],
      title: titles[index],
    }));
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-2 border rounded shadow-sm">
          <p className="font-semibold">{data.title}</p>
          <p className="text-sm text-muted-foreground">Cluster: {data.cluster}</p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Performing entity linking...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h2 className="text-2xl font-bold">Server Entity Linking</h2>
        
        <div className="flex items-center gap-4">
          <Tabs
            value={visualizationType}
            onValueChange={(value) => setVisualizationType(value as 'pca' | 'tsne')}
            className="w-[200px]"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="pca">PCA</TabsTrigger>
              <TabsTrigger value="tsne">t-SNE</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {error ? (
        <div className="bg-red-50 p-4 rounded-md text-red-800">
          <p>{error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Cluster Visualization ({visualizationType.toUpperCase()})</CardTitle>
                <CardDescription>
                  Visual representation of server clusters based on feature similarity
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[500px]">
                  {visualizationData ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <CartesianGrid />
                        <XAxis type="number" dataKey="x" name="x" />
                        <YAxis type="number" dataKey="y" name="y" />
                        <ZAxis type="number" range={[100]} />
                        <Tooltip content={<CustomTooltip />} />
                        
                        {visualizationData && 
                          [...new Set(visualizationData[visualizationType].clusters)].map((clusterIndex) => {
                            const clusterData = prepareScatterData().filter(
                              item => item.cluster === clusterIndex
                            );
                            
                            return (
                              <Scatter
                                key={clusterIndex}
                                name={`Cluster ${clusterIndex}`}
                                data={clusterData}
                                fill={COLORS[clusterIndex % COLORS.length]}
                              />
                            );
                          })}
                      </ScatterChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-muted-foreground">No visualization data available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
          
          <div>
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Cluster Summaries</CardTitle>
                <CardDescription>Key characteristics of each cluster</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                  {clusterSummaries.length > 0 ? (
                    clusterSummaries.map(cluster => (
                      <div key={cluster.cluster_id} className="p-4 border rounded-md">
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: COLORS[cluster.cluster_id % COLORS.length] }}
                          ></div>
                          <h3 className="font-semibold">Cluster {cluster.cluster_id}</h3>
                        </div>
                        
                        <div className="text-sm">
                          <p><span className="font-medium">Size:</span> {cluster.size} servers</p>
                          <p><span className="font-medium">Avg. Features:</span> {cluster.avg_feature_count.toFixed(1)}</p>
                          <p><span className="font-medium">Avg. Tools:</span> {cluster.avg_tool_count.toFixed(1)}</p>
                        </div>
                        
                        <div className="mt-2">
                          <p className="text-sm font-medium mb-1">Common Tags:</p>
                          <div className="flex flex-wrap gap-1">
                            {cluster.common_tags.map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {tag.replace(/^#\s*/, '')}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        
                        <div className="mt-2">
                          <p className="text-sm font-medium mb-1">Servers:</p>
                          <ul className="text-sm space-y-1">
                            {cluster.servers.slice(0, 5).map(server => (
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
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <p className="text-muted-foreground">No cluster summaries available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClusteringView;
