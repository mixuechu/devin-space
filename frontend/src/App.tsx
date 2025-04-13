import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import ServerExplorerNew from './components/ServerExplorerNew';
import ClusteringView from './components/ClusteringView';
import RecommendationView from './components/RecommendationView';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Loader2, BarChart, Server, Network, Search } from 'lucide-react';

const App: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 5000);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto py-4">
          <h1 className="text-2xl font-bold">MCP Server Analysis System</h1>
        </div>
      </header>
      
      <main className="container mx-auto py-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="max-w-md w-full p-6 bg-card rounded-lg shadow-sm border text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Loading MCP Server Data</h2>
              <p className="text-muted-foreground">
                Please wait while we prepare the server data for analysis...
              </p>
            </div>
          </div>
        ) : (
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
              <ServerExplorerNew />
            </TabsContent>
            
            <TabsContent value="clustering">
              <ClusteringView />
            </TabsContent>
            
            <TabsContent value="recommendations">
              <RecommendationView />
            </TabsContent>
          </Tabs>
        )}
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
