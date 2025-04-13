import React, { useState, useEffect } from 'react';
import { Server } from '../services/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Loader2, Search, Tag, Github, FileText, Wrench, ChevronLeft, ChevronRight } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';

function ServerExplorer() {
  const [servers, setServers] = useState<Server[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [clusterFilter, setClusterFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [clusters, setClusters] = useState<number[]>([]);
  const [page, setPage] = useState<number>(1);
  const [totalServers, setTotalServers] = useState<number>(0);
  const [selectedServer, setSelectedServer] = useState<Server | null>(null);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const pageSize = 30; // Increased page size for better browsing

  useEffect(() => {
    const initializeData = async () => {
      try {
        console.log('Fetching server data...');
        await fetchServers();
      } catch (err) {
        console.error('Error initializing data:', err);
        setError('Failed to initialize data. Please try again later.');
        setLoading(false);
      }
    };

    initializeData();
  }, []);
  
  const fetchServers = async () => {
    try {
      setLoading(true);
      
      const skip = (page - 1) * pageSize;
      
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      
      const queryParams = new URLSearchParams();
      queryParams.append('skip', skip.toString());
      queryParams.append('limit', pageSize.toString());
      if (searchTerm) queryParams.append('search', searchTerm);
      if (clusterFilter !== 'all') queryParams.append('cluster_id', clusterFilter);
      
      const response = await fetch(`${apiUrl}/servers?${queryParams.toString()}`, {
        headers: {
          'Authorization': 'Basic ' + btoa('user:9447d682f523e92d92e6fce76fa26e93')
        }
      }).then(res => res.json());
      
      setServers(response.servers);
      setTotalServers(response.total);
      
      const uniqueClusters = Array.from(
        new Set(response.servers.map((server: Server) => server.cluster_id).filter(Boolean))
      );
      setClusters(uniqueClusters as number[]);
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching servers:', err);
      setError('Failed to load servers. Please try again later.');
      setLoading(false);
    }
  };

  useEffect(() => {
    const handleFiltersChange = async () => {
      await fetchServers();
    };
    
    handleFiltersChange();
  }, [searchTerm, clusterFilter, page]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setPage(1);
  };

  const handleClusterFilterChange = (value: string) => {
    setClusterFilter(value);
    setPage(1);
  };
  
  const handleViewDetails = async (server: Server) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const serverDetails = await fetch(`${apiUrl}/servers/${server.id}`, {
        headers: {
          'Authorization': 'Basic ' + btoa('user:9447d682f523e92d92e6fce76fa26e93')
        }
      }).then(res => res.json());
      setSelectedServer(serverDetails);
      setShowDetails(true);
    } catch (err) {
      console.error('Error fetching server details:', err);
      setError('Failed to load server details. Please try again later.');
    }
  };
  
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const getQualityColor = (score?: number) => {
    if (!score) return 'bg-gray-200';
    if (score >= 90) return 'bg-green-500';
    if (score >= 80) return 'bg-green-400';
    if (score >= 70) return 'bg-yellow-400';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">
          Loading servers...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 p-4 rounded-md text-red-800">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-grow">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search servers by name, description, or tags..."
            className="pl-8"
            value={searchTerm}
            onChange={handleSearchChange}
          />
        </div>
        
        <div className="w-full md:w-64">
          <Select value={clusterFilter} onValueChange={handleClusterFilterChange}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by cluster" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Clusters</SelectItem>
              {clusters.map(clusterId => (
                <SelectItem key={clusterId} value={clusterId.toString()}>
                  Cluster {clusterId}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {servers.length > 0 ? (
          servers.map(server => (
            <Card key={server.id} className="flex flex-col h-full">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg">{server.title}</CardTitle>
                  {server.overall_score && (
                    <div className="flex items-center">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${getQualityColor(
                          server.overall_score
                        )}`}
                      >
                        {Math.round(server.overall_score)}
                      </div>
                    </div>
                  )}
                </div>
                <CardDescription>{server.description}</CardDescription>
              </CardHeader>
              
              <CardContent className="flex-grow">
                <div className="flex flex-wrap gap-2 mb-4">
                  {server.tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      {tag.replace(/^#\s*/, '')}
                    </Badge>
                  ))}
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span>{server.word_count} words</span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                    <span>{server.tool_count} tools</span>
                  </div>
                  
                  {server.has_github && (
                    <div className="flex items-center gap-2">
                      <Github className="h-4 w-4 text-muted-foreground" />
                      <span>GitHub</span>
                    </div>
                  )}
                  
                  {server.has_faq && (
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span>FAQ</span>
                    </div>
                  )}
                </div>
                
                {server.cluster_id !== undefined && (
                  <div className="mt-4">
                    <Badge variant="outline">Cluster {server.cluster_id}</Badge>
                  </div>
                )}
              </CardContent>
              
              <CardFooter className="border-t pt-4">
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => handleViewDetails(server)}
                >
                  View Details
                </Button>
              </CardFooter>
            </Card>
          ))
        ) : (
          <div className="col-span-full text-center py-12">
            <p className="text-muted-foreground">No servers found matching your criteria.</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setSearchTerm('');
                setClusterFilter('all');
              }}
            >
              Clear Filters
            </Button>
          </div>
        )}
      </div>
      
      {/* Pagination */}
      {totalServers > pageSize && (
        <div className="flex justify-center mt-6">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(Math.max(1, page - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="sr-only">Previous Page</span>
            </Button>
            
            <div className="text-sm">
              Page {page} of {Math.ceil(totalServers / pageSize)}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(Math.min(Math.ceil(totalServers / pageSize), page + 1))}
              disabled={page >= Math.ceil(totalServers / pageSize)}
            >
              <ChevronRight className="h-4 w-4" />
              <span className="sr-only">Next Page</span>
            </Button>
          </div>
        </div>
      )}
      
      {/* Server Details Dialog */}
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          {selectedServer && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl flex items-center justify-between">
                  {selectedServer.title}
                  {selectedServer.overall_score && (
                    <Badge className={`${getQualityColor(selectedServer.overall_score)} text-white`}>
                      Score: {Math.round(selectedServer.overall_score)}
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription className="text-base">
                  {selectedServer.description}
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 my-4">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedServer.tags.map((tag, index) => (
                      <Badge key={index} variant="secondary">
                        {tag.replace(/^#\s*/, '')}
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold mb-2">Metrics</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-muted rounded-md p-3">
                      <div className="text-sm text-muted-foreground">Code Quality</div>
                      <div className="text-2xl font-bold">{selectedServer.code_quality_score}</div>
                    </div>
                    <div className="bg-muted rounded-md p-3">
                      <div className="text-sm text-muted-foreground">Tool Completeness</div>
                      <div className="text-2xl font-bold">{selectedServer.tool_completeness_score}</div>
                    </div>
                    <div className="bg-muted rounded-md p-3">
                      <div className="text-sm text-muted-foreground">Documentation</div>
                      <div className="text-2xl font-bold">{selectedServer.documentation_quality_score}</div>
                    </div>
                    <div className="bg-muted rounded-md p-3">
                      <div className="text-sm text-muted-foreground">Runtime Stability</div>
                      <div className="text-2xl font-bold">{selectedServer.runtime_stability_score}</div>
                    </div>
                    <div className="bg-muted rounded-md p-3">
                      <div className="text-sm text-muted-foreground">Business Value</div>
                      <div className="text-2xl font-bold">{selectedServer.business_value_score}</div>
                    </div>
                  </div>
                </div>
                
                {selectedServer.raw_data && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Raw Data</h3>
                    <div className="bg-muted p-3 rounded-md overflow-x-auto">
                      <pre className="text-xs">{JSON.stringify(selectedServer.raw_data, null, 2)}</pre>
                    </div>
                  </div>
                )}
                
                {selectedServer.similar_servers && selectedServer.similar_servers.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Similar Servers</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {selectedServer.similar_servers.map((similar, index) => (
                        <div key={index} className="border rounded-md p-2">
                          <div className="font-medium">{similar.title}</div>
                          <div className="text-sm text-muted-foreground truncate">{similar.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              <DialogFooter>
                <Button onClick={() => setShowDetails(false)}>Close</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export { ServerExplorer as default };
