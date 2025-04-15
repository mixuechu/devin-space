import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getServers, getServerDetails } from '../services/api';
import type { Server, ClusterSummary } from '../types';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Loader2, Search, Tag, Github, FileText, Wrench, ChevronLeft, ChevronRight } from 'lucide-react';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { staticData } from '../store/dataCache';
import { useVirtualizer } from '@tanstack/react-virtual';
import { cn } from '../lib/utils';

interface ClusterInfo {
  cluster_id: number;
  cluster_name: string;
  description?: string;
  common_tags: string[];
}

interface ServerWithExtras extends Omit<Server, 'cluster_info'> {
  tools?: string[];
  cluster_info?: ClusterInfo;
}

interface ClusterOption {
  value: string;
  label: string;
  serverCount: number;
  description?: string;
  common_tags: string[];
  servers: ServerWithExtras[];
}

const ServerExplorer: React.FC = () => {
  const [servers, setServers] = useState<ServerWithExtras[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [clusterFilter, setClusterFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [allServers, setAllServers] = useState<ServerWithExtras[]>([]);
  const [filteredServers, setFilteredServers] = useState<ServerWithExtras[]>([]);
  const [page, setPage] = useState<number>(1);
  const [totalServers, setTotalServers] = useState<number>(0);
  const [selectedServer, setSelectedServer] = useState<ServerWithExtras | null>(null);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const pageSize = 30;
  const [clusterSearchOpen, setClusterSearchOpen] = useState(false);
  const [clusterSearchValue, setClusterSearchValue] = useState('');
  const [clusterDropdownPage, setClusterDropdownPage] = useState(1);
  const clusterDropdownPageSize = 15;
  const [debouncedSearchValue, setDebouncedSearchValue] = useState(clusterSearchValue);
  const [searchResults, setSearchResults] = useState<{
    items: any[];
    total: number;
    page: number;
    page_size: number;
  } | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // 优化集群选项计算
  const clusterOptions = useMemo(() => {
    if (!allServers.length) return { all: { value: 'all', label: 'All Clusters', serverCount: 0 }, options: [], total: 0 };

    const clusterMap = new Map<string, ClusterOption>();
    let totalServers = 0;
    
    // 收集集群信息和服务器数量
    allServers.forEach(server => {
      if (server.cluster_info) {
        const clusterId = server.cluster_info.cluster_id.toString();
        if (!clusterMap.has(clusterId)) {
          clusterMap.set(clusterId, {
            value: clusterId,
            label: server.cluster_info.cluster_name,
            serverCount: 1,
            description: server.cluster_info.description,
            common_tags: server.cluster_info.common_tags || [],
            servers: [server]
          });
        } else {
          const cluster = clusterMap.get(clusterId)!;
          cluster.serverCount++;
          cluster.servers.push(server);
        }
        totalServers++;
      }
    });
    
    // 转换为数组并排序
    const sortedOptions = Array.from(clusterMap.values())
      .sort((a, b) => b.serverCount - a.serverCount);
    
    return {
      all: { value: 'all', label: 'All Clusters', serverCount: allServers.length },
      options: sortedOptions,
      total: sortedOptions.length
    };
  }, [allServers]);

  // 优化搜索逻辑
  const searchClusters = useCallback(async (query: string, page: number) => {
    const normalizedQuery = query.trim().toLowerCase();
    
    if (!normalizedQuery) {
      return {
        items: clusterOptions.options.slice(
          (page - 1) * clusterDropdownPageSize,
          page * clusterDropdownPageSize
        ),
        total: clusterOptions.options.length
      };
    }
    
    const matchedClusters = clusterOptions.options.filter(option => 
      option.label.toLowerCase().includes(normalizedQuery) ||
      option.description?.toLowerCase().includes(normalizedQuery) ||
      option.common_tags?.some(tag => tag.toLowerCase().includes(normalizedQuery))
    );
    
    return {
      items: matchedClusters.slice(
        (page - 1) * clusterDropdownPageSize,
        page * clusterDropdownPageSize
      ),
      total: matchedClusters.length
    };
  }, [clusterOptions, clusterDropdownPageSize]);

  // 优化数据初始化
  const initializeData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const clusteringData = await staticData.getClustering();
      if (!clusteringData?.cluster_summaries) {
        throw new Error('Clustering data not available');
      }
      
      setClusters(clusteringData.cluster_summaries);
      
      const cachedServers = staticData.getServers();
      if (cachedServers?.servers) {
        const clusterMap = new Map(
          clusteringData.cluster_summaries.map(c => [c.cluster_id, c])
        );
        
        const serversWithClusterInfo = cachedServers.servers.map(server => ({
          ...server,
          cluster_info: server.cluster_id != null ? clusterMap.get(server.cluster_id) : undefined
        }));
        
        setAllServers(serversWithClusterInfo);
        setFilteredServers(serversWithClusterInfo);
        setServers(serversWithClusterInfo.slice(0, pageSize));
        setTotalServers(serversWithClusterInfo.length);
      } else {
        await fetchServers(clusteringData.cluster_summaries);
      }
    } catch (err) {
      console.error('Error initializing data:', err);
      setError('Failed to initialize data. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  // 添加初始化effect
  useEffect(() => {
    initializeData();
  }, [initializeData]);

  // 使用虚拟滚动优化服务器列表渲染
  const parentRef = React.useRef<HTMLDivElement>(null);
  
  const rowVirtualizer = useVirtualizer({
    count: Math.ceil((filteredServers?.length ?? 0) / 3),
    getScrollElement: () => parentRef.current,
    estimateSize: () => 280,
    overscan: 5,
  });

  // 使用防抖处理搜索输入
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchValue(clusterSearchValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [clusterSearchValue]);

  // 处理搜索
  useEffect(() => {
    const searchClusters = async () => {
      try {
        setIsSearching(true);
        const response = await fetch(
          `/api/clusters/search?${new URLSearchParams({
            query: debouncedSearchValue,
            page: clusterDropdownPage.toString(),
            page_size: clusterDropdownPageSize.toString()
          })}`
        );
        
        if (!response.ok) {
          throw new Error('Search failed');
        }
        
        const data = await response.json();
        setSearchResults(data);
      } catch (error) {
        console.error('Search failed:', error);
        setSearchResults(null);
      } finally {
        setIsSearching(false);
      }
    };

    searchClusters();
  }, [debouncedSearchValue, clusterDropdownPage]);

  // 处理搜索结果
  const filteredClusterOptions = useMemo(() => {
    if (!searchResults && !clusterSearchValue) {
      return {
        items: clusterOptions.options.slice(0, clusterDropdownPageSize),
        total: clusterOptions.total
      };
    }

    if (!searchResults) {
      const normalizedQuery = clusterSearchValue.toLowerCase().trim();
      const filteredClusters = clusterOptions.options.filter(option =>
        option.label.toLowerCase().includes(normalizedQuery) ||
        option.description?.toLowerCase().includes(normalizedQuery) ||
        option.common_tags.some(tag => tag.toLowerCase().includes(normalizedQuery))
      );

      return {
        items: filteredClusters.slice(
          (clusterDropdownPage - 1) * clusterDropdownPageSize,
          clusterDropdownPage * clusterDropdownPageSize
        ),
        total: filteredClusters.length
      };
    }

    return searchResults;
  }, [searchResults, clusterSearchValue, clusterOptions, clusterDropdownPage, clusterDropdownPageSize]);

  // 本地过滤和分页
  useEffect(() => {
    if (allServers.length === 0) return;

    let filteredServers = [...allServers];

    // 应用搜索过滤
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filteredServers = filteredServers.filter(server => 
        server.title.toLowerCase().includes(searchLower) ||
        server.description.toLowerCase().includes(searchLower) ||
        server.tags.some(tag => tag.toLowerCase().includes(searchLower))
      );
    }

    // 应用集群过滤
    if (clusterFilter !== 'all') {
      filteredServers = filteredServers.filter(
        server => server.cluster_id === parseInt(clusterFilter)
      );
    }

    // 更新总数和当前页数据
    setTotalServers(filteredServers.length);
    setFilteredServers(filteredServers);
    const start = (page - 1) * pageSize;
    setServers(filteredServers.slice(start, start + pageSize));
  }, [allServers, searchTerm, clusterFilter, page]);

  const fetchServers = async (clusterSummaries: ClusterSummary[]) => {
    try {
      // 获取第一页数据和总数
      const response = await getServers({
        limit: 100,
        offset: 0
      });
      
      if (!response?.servers) {
        throw new Error('Failed to fetch servers data');
      }
      
      // 获取所有服务器数据
      const allServersData = [...response.servers];
      const totalPages = Math.ceil(response.total / 100);
      
      // 如果有更多页，继续获取
      if (totalPages > 1) {
        const otherPagesPromises = Array.from({ length: totalPages - 1 }, (_, i) =>
          getServers({ limit: 100, offset: (i + 1) * 100 })
        );
        
        const otherPagesResults = await Promise.all(otherPagesPromises);
        otherPagesResults.forEach(result => {
          if (result?.servers) {
            allServersData.push(...result.servers);
          }
        });
      }

      // 为每个服务器添加集群信息
      const clusterMap = new Map(
        clusterSummaries.map(c => [c.cluster_id, c])
      );
      
      const serversWithClusterInfo = allServersData.map(server => ({
        ...server,
        cluster_info: server.cluster_id != null ? clusterMap.get(server.cluster_id) : undefined
      }));
      
      setAllServers(serversWithClusterInfo);
      setFilteredServers(serversWithClusterInfo);
      setServers(serversWithClusterInfo.slice(0, pageSize));
      setTotalServers(serversWithClusterInfo.length);
      
      // 缓存带有集群信息的服务器数据
      staticData.setServers({
        servers: serversWithClusterInfo,
        total: serversWithClusterInfo.length
      });
    } catch (err) {
      console.error('Error fetching servers:', err);
      setError('Failed to load servers. Please try again later.');
      throw err; // 重新抛出错误以便上层处理
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setPage(1); // 重置页码
  };

  const handleClusterFilterChange = (value: string) => {
    setClusterFilter(value);
    setPage(1); // 重置页码
  };
  
  const handleViewDetails = async (server: ServerWithExtras) => {
    try {
      const serverDetails = await getServerDetails(server.server_id);
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

  const handleClusterDropdownPageChange = (newPage: number) => {
    setClusterDropdownPage(newPage);
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
    <div className="container mx-auto p-4">
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <form onSubmit={(e) => e.preventDefault()} className="flex flex-grow gap-2">
          <div className="relative flex-grow">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="输入服务器名称、描述或标签进行搜索..."
              className="pl-8"
              value={searchTerm}
              onChange={handleSearchChange}
            />
          </div>
        </form>
        
        <div className="w-full md:w-72">
          <Popover open={clusterSearchOpen} onOpenChange={setClusterSearchOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={clusterSearchOpen}
                className="w-full justify-between"
              >
                {clusterFilter === 'all' 
                  ? 'All Clusters'
                  : clusterOptions.options.find(option => option.value === clusterFilter)?.label || 'Select Cluster'}
                <ChevronLeft className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0">
              <Command>
                <CommandInput
                  placeholder="搜索集群（支持名称、标签，支持模糊匹配）..."
                  value={clusterSearchValue}
                  onValueChange={(value) => {
                    setClusterSearchValue(value);
                    setClusterDropdownPage(1);
                  }}
                />
                <CommandEmpty>
                  {isSearching ? (
                    <div className="py-6 text-center text-sm">
                      <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
                      搜索中...
                    </div>
                  ) : (
                    "没有找到匹配的集群"
                  )}
                </CommandEmpty>
                <CommandGroup>
                  {!isSearching && (
                    <>
                      <CommandItem
                        key="all"
                        value="all"
                        onSelect={() => {
                          handleClusterFilterChange('all');
                          setClusterSearchOpen(false);
                        }}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>All Clusters</span>
                          <Badge variant="secondary">{clusterOptions.all.serverCount} servers</Badge>
                        </div>
                      </CommandItem>
                      {filteredClusterOptions.items.map((option: ClusterOption) => (
                        <CommandItem
                          key={option.value}
                          value={option.value}
                          onSelect={() => {
                            handleClusterFilterChange(option.value);
                            setClusterSearchOpen(false);
                          }}
                        >
                          <div className="flex items-center justify-between w-full">
                            <div className="flex flex-col">
                              <span>{option.label}</span>
                              {option.common_tags.length > 0 && (
                                <span className="text-xs text-muted-foreground">
                                  {option.common_tags.slice(0, 3).join(', ')}
                                </span>
                              )}
                            </div>
                            <Badge variant="secondary">{option.serverCount} servers</Badge>
                          </div>
                        </CommandItem>
                      ))}
                    </>
                  )}
                </CommandGroup>
                {!isSearching && filteredClusterOptions.total > clusterDropdownPageSize && (
                  <div className="flex items-center justify-center gap-2 p-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleClusterDropdownPageChange(Math.max(1, clusterDropdownPage - 1))}
                      disabled={clusterDropdownPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      {clusterDropdownPage} / {Math.ceil(filteredClusterOptions.total / clusterDropdownPageSize)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleClusterDropdownPageChange(
                        Math.min(
                          Math.ceil(filteredClusterOptions.total / clusterDropdownPageSize),
                          clusterDropdownPage + 1
                        )
                      )}
                      disabled={clusterDropdownPage >= Math.ceil(filteredClusterOptions.total / clusterDropdownPageSize)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </Command>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        {servers.map((server) => (
          <ServerCard
            key={server.server_id}
            server={server}
            onClick={() => {
              setSelectedServer(server);
              setShowDetails(true);
            }}
            score={server.overall_score ?? 0}
          />
        ))}
      </div>
      
      {/* Pagination */}
      {totalServers > pageSize && (
        <div className="flex justify-center py-4 border-t">
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
                    {selectedServer.tags.map((tag: string, index: number) => (
                      <Badge key={index} variant="secondary" className="flex items-center gap-1">
                        <Tag className="h-3 w-3" />
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
                      {selectedServer.similar_servers.map((similar: { server_id: string; title: string; description: string }, index: number) => (
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

interface ServerCardProps {
  server: ServerWithExtras;
  onClick: () => void;
  score: number;
}

const ServerCard: React.FC<ServerCardProps> = React.memo(
  ({ server, onClick, score }) => (
    <Card
      className="cursor-pointer hover:shadow-lg transition-shadow bg-card"
      onClick={onClick}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex justify-between items-start gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-semibold truncate">{server.title}</CardTitle>
            <CardDescription className="mt-1 text-sm line-clamp-2">{server.description}</CardDescription>
          </div>
          <Badge className={cn(
            "shrink-0",
            score >= 90 ? "bg-green-500" :
            score >= 80 ? "bg-green-400" :
            score >= 70 ? "bg-yellow-400" :
            score >= 60 ? "bg-yellow-500" :
            "bg-red-500",
            "text-white"
          )}>
            {score.toFixed(1)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-2">
        <div className="flex flex-wrap gap-1.5">
          {server.tags.slice(0, 5).map((tag: string) => (
            <Badge key={tag} variant="outline" className="flex items-center gap-1 text-xs py-0 h-5">
              <Tag className="h-3 w-3" />
              {tag}
            </Badge>
          ))}
          {server.tags.length > 5 && (
            <Badge variant="outline" className="text-xs py-0 h-5">+{server.tags.length - 5} more</Badge>
          )}
        </div>
      </CardContent>
      <CardFooter className="px-4 py-3 flex justify-between text-sm text-muted-foreground border-t">
        <div className="flex items-center gap-2 truncate">
          <FileText className="h-4 w-4 shrink-0" />
          <span className="truncate">{server.cluster_info?.cluster_name || 'Uncategorized'}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Wrench className="h-4 w-4" />
          <span>Tools: {server.tools?.length || 0}</span>
        </div>
      </CardFooter>
    </Card>
  )
);

export default ServerExplorer;
