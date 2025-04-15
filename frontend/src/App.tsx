import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import ServerExplorer from './components/ServerExplorer';
import ClusteringView from './components/ClusteringView';
import RecommendationView from './components/RecommendationView';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Loader2, BarChart, Server, Network, Search, RefreshCw } from 'lucide-react';
import { clusterServers, getServers } from './services/api';
import { staticData } from './store/dataCache';
import { Button } from './components/ui/button';
import { generateClusterNames } from './utils/clusterUtils';

const App: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [initError, setInitError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const initializeApp = async (forceRefresh = false) => {
    try {
      setLoading(true);
      
      // 如果强制刷新或没有缓存的聚类数据，获取新数据
      if (forceRefresh || !staticData.getClustering()) {
        if (forceRefresh) {
          console.log('Force refreshing all data...');
          staticData.clearAll();
        } else {
          console.log('Preloading clustering data...');
        }
        
        // 获取并处理集群数据
        const clusteringData = await clusterServers(0.7);
        if (clusteringData && clusteringData.cluster_summaries) {
          // 生成集群名称
          const namedClusters = generateClusterNames(clusteringData.cluster_summaries);
          
          // 创建服务器ID到集群的映射
          const serverClusterMap = new Map();
          namedClusters.forEach(cluster => {
            cluster.servers.forEach(server => {
              serverClusterMap.set(server.id, cluster);
            });
          });
          
          // 保存集群数据到静态存储
          staticData.setClustering({
            visualization_data: clusteringData.visualization_data,
            cluster_summaries: namedClusters
          });

          // 获取服务器数据
          const serversResponse = await getServers({
            limit: 100,  // 每页100条数据
            offset: 0
          });
          
          if (serversResponse.servers) {
            // 获取所有服务器数据
            const allServersData = [];
            const totalPages = Math.ceil(serversResponse.total / 100);
            
            // 先添加第一页数据
            allServersData.push(...serversResponse.servers);
            
            // 如果有更多页，继续获取
            if (totalPages > 1) {
              const otherPagesPromises = Array.from({ length: totalPages - 1 }, (_, i) =>
                getServers({ limit: 100, offset: (i + 1) * 100 })
              );
              
              const otherPagesResults = await Promise.all(otherPagesPromises);
              otherPagesResults.forEach(result => {
                if (result.servers) {
                  allServersData.push(...result.servers);
                }
              });
            }
            
            // 为服务器数据关联集群信息
            const serversWithClusterInfo = allServersData.map(server => {
              const cluster = serverClusterMap.get(server.server_id);
              if (!cluster) {
                console.warn(`No cluster found for server ${server.server_id}`);
              }
              return {
                ...server,
                cluster_id: cluster?.cluster_id,
                cluster_name: cluster?.cluster_name,
                cluster_info: cluster
              };
            });

            // 保存服务器数据到静态存储
            staticData.setServers({
              servers: serversWithClusterInfo,
              total: serversResponse.total
            });
          }
        }
      }
    } catch (err) {
      console.error('Error initializing data:', err);
      setInitError('Failed to initialize data. Some features may be limited.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    initializeApp();
  }, []);

  const handleForceRefresh = async () => {
    setRefreshing(true);
    await initializeApp(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b">
          <div className="container mx-auto py-4">
            <h1 className="text-2xl font-bold">MCP Server Analysis System</h1>
          </div>
        </header>
        <main className="container mx-auto py-6">
          <div className="flex flex-col items-center justify-center py-12">
            <div className="max-w-md w-full p-6 bg-card rounded-lg shadow-sm border text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Initializing System</h2>
              <p className="text-muted-foreground">
                Please wait while we prepare the analysis system...
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold">MCP Server Analysis System</h1>
              {initError && (
                <div className="mt-2 text-sm text-red-600">
                  {initError}
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleForceRefresh}
              disabled={refreshing}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing...' : 'Force Refresh'}
            </Button>
          </div>
        </div>
      </header>
      
      <main className="container mx-auto py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex justify-between items-center mb-6">
            <TabsList>
              <TabsTrigger value="dashboard" className="flex items-center gap-1">
                <BarChart className="h-4 w-4" />
                Dashboard
              </TabsTrigger>
              <TabsTrigger value="servers" className="flex items-center gap-1">
                <Server className="h-4 w-4" />
                Servers
              </TabsTrigger>
              <TabsTrigger value="clustering" className="flex items-center gap-1">
                <Network className="h-4 w-4" />
                Clustering
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="flex items-center gap-1">
                <Search className="h-4 w-4" />
                Recommendations
              </TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="dashboard">
            <Dashboard />
          </TabsContent>
          
          <TabsContent value="servers">
            <ServerExplorer />
          </TabsContent>
          
          <TabsContent value="clustering">
            <ClusteringView />
          </TabsContent>
          
          <TabsContent value="recommendations">
            <RecommendationView />
          </TabsContent>
        </Tabs>
      </main>
      
      <footer className="border-t mt-auto">
        <div className="container mx-auto py-4">
          <p className="text-sm text-muted-foreground">
            MCP Server Analysis System &copy; {new Date().getFullYear()}
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
