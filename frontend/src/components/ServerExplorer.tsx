import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { getServers, getServerDetails } from '../services/api';
import type { Server } from '../types';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Loader2, Search, Tag, Github, FileText, Wrench, ChevronLeft, ChevronRight, Check, ChevronsUpDown } from 'lucide-react';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { staticData } from '../store/dataCache';
import { useVirtualizer } from '@tanstack/react-virtual';
import { cn } from '../lib/utils';
import { ServerWithExtras, ClusterInfo, APIServer } from '../types/server';
import { API_URL } from '../services/api';

interface ClusterOption {
  value: string;
  label: string;
  count: number;
  common_tags: string[];
  serverCount: number;
}

interface ClusterSearchResult {
  items: ClusterOption[];
  total: number;
}

const ServerExplorer: React.FC = () => {
  const [servers, setServers] = useState<ServerWithExtras[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [clusterFilter, setClusterFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedServer, setSelectedServer] = useState<ServerWithExtras | null>(null);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const [clusterSearchOpen, setClusterSearchOpen] = useState(false);
  const [clusterSearchValue, setClusterSearchValue] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [debouncedSearchValue, setDebouncedSearchValue] = useState('');
  const [searchResults, setSearchResults] = useState<ClusterSearchResult>({ items: [], total: 0 });
  const [clusterDropdownPage, setClusterDropdownPage] = useState(1);
  const [page, setPage] = useState(1);
  const pageSize = 30;
  const clusterDropdownPageSize = 15;
  const [totalServers, setTotalServers] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const parentRef = useRef<HTMLDivElement | null>(null);

  const transformServerToExtras = (server: Server): ServerWithExtras => {
    if (!server.cluster_info) {
      return {
        ...server,
        cluster_info: undefined
      };
    }

    // 确保 cluster_info 包含所有必要的字段
    const cluster_info: ClusterInfo = {
      cluster_id: server.cluster_info.cluster_id,
      name: server.cluster_info.name,
      common_tags: server.cluster_info.common_tags || [],
      server_count: (server.cluster_info as any).server_count || 1
    };

    return {
      ...server,
      cluster_info
    };
  };

  const serversData = staticData.getServers();
  const allServers = useMemo(() => {
    return (serversData?.servers || []).map(transformServerToExtras);
  }, [serversData]);

  const clusterOptions = useMemo(() => {
    const clusterMap = new Map<string, { name: string; count: number }>();
    
    allServers.forEach(server => {
      if (server.cluster_info) {
        const { cluster_id, name } = server.cluster_info;
        const existing = clusterMap.get(cluster_id);
        if (existing) {
          existing.count++;
        } else {
          clusterMap.set(cluster_id, { name, count: 1 });
        }
      }
    });

    return Array.from(clusterMap.entries())
      .map(([value, { name, count }]) => ({
        value,
        label: `${name} (${count})`,
        count,
        common_tags: [],
        serverCount: count
      }))
      .sort((a, b) => b.count - a.count);
  }, [allServers]);

  const filteredServers = useMemo(() => {
    return allServers.filter(server => {
      if (!clusterFilter) return true;
      return server.cluster_info?.cluster_id === clusterFilter;
    });
  }, [allServers, clusterFilter]);

  const handleClusterFilterChange = useCallback((value: string | null) => {
    setClusterFilter(value);
    setPage(1); // Reset to first page when changing filter
    setOpen(false);
  }, []);

  // 处理搜索输入变化
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    // 清除之前的定时器
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // 设置新的定时器
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchTerm(value);
      setPage(1); // 重置页码
    }, 500); // 500ms 延迟
  };

  // 处理搜索按钮点击
  const handleSearchClick = () => {
    setDebouncedSearchTerm(searchTerm);
    setPage(1);
  };

  // 处理回车键搜索
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearchClick();
    }
  };

  // 更新 useEffect 中的 fetchServers 函数
  useEffect(() => {
    const fetchServers = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await getServers(
          page, 
          pageSize, 
          clusterFilter || undefined,
          debouncedSearchTerm || undefined
        );
        
        // 获取集群数据
        const clusteringData = staticData.getClustering();
        console.log('Clustering Data:', clusteringData);
        
        // 确保使用字符串类型的 cluster_id
        const clusterMap = clusteringData?.cluster_summaries
          ? new Map(clusteringData.cluster_summaries.map(c => [c.cluster_id.toString(), {
              ...c,
              name: c.cluster_name  // 直接使用 cluster_name 作为 name
            }]))
          : new Map();
          
        console.log('Cluster Map size:', clusterMap.size);
        console.log('Cluster Map entries:', Array.from(clusterMap.entries()));
        
        // 转换 APIServer 到 ServerWithExtras
        const transformedServers: ServerWithExtras[] = (response.servers as APIServer[]).map(server => {
          const clusterIdStr = server.cluster_id?.toString();
          const clusterData = clusterIdStr ? clusterMap.get(clusterIdStr) : undefined;
          
          console.log('Processing server:', {
            server_id: server.server_id,
            cluster_id: server.cluster_id,
            cluster_id_str: clusterIdStr,
            has_cluster_info: clusterIdStr ? clusterMap.has(clusterIdStr) : false,
            cluster_info: clusterData
          });
          
          const clusterInfo = clusterData
            ? {
                cluster_id: clusterIdStr!,
                name: clusterData.name,
                common_tags: clusterData.common_tags || [],
                server_count: clusterData.server_count || 1
              }
            : undefined;

          return {
            ...server,
            cluster_info: clusterInfo
          };
        });
        
        setServers(transformedServers);
        setTotalServers(response.total);
        setTotalPages(Math.ceil(response.total / pageSize));
      } catch (err) {
        console.error('Error fetching servers:', err);
        setError('Failed to load servers');
      } finally {
        setLoading(false);
      }
    };

    fetchServers();
  }, [page, clusterFilter, debouncedSearchTerm]);

  // 优化搜索逻辑
  const searchClusters = useCallback(async (query: string, page: number) => {
    const normalizedQuery = query.trim().toLowerCase();
    
    if (!normalizedQuery) {
      return {
        items: clusterOptions.slice(
          (page - 1) * clusterDropdownPageSize,
          page * clusterDropdownPageSize
        ),
        total: clusterOptions.length
      };
    }
    
    const matchedClusters = clusterOptions.filter(option => 
      option.label.toLowerCase().includes(normalizedQuery)
    );
    
    return {
      items: matchedClusters.slice(
        (page - 1) * clusterDropdownPageSize,
        page * clusterDropdownPageSize
      ),
      total: matchedClusters.length
    };
  }, [clusterOptions, clusterDropdownPageSize]);

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
          `${API_URL}/api/clusters/search?${new URLSearchParams({
            query: debouncedSearchValue,
            page: clusterDropdownPage.toString(),
            page_size: clusterDropdownPageSize.toString()
          })}`
        );
        
        if (!response.ok) {
          console.error('Search failed:', await response.text());
          // 如果搜索失败，回退到本地过滤
          const normalizedQuery = debouncedSearchValue.trim().toLowerCase();
          const filteredClusters = clusterOptions.filter(option => 
            option.label.toLowerCase().includes(normalizedQuery)
          );
          
          setSearchResults({
            items: filteredClusters.slice(
              (clusterDropdownPage - 1) * clusterDropdownPageSize,
              clusterDropdownPage * clusterDropdownPageSize
            ),
            total: filteredClusters.length
          });
          return;
        }
        
        const data = await response.json();
        setSearchResults(data);
      } catch (error) {
        console.error('Search failed:', error);
        // 如果发生错误，回退到本地过滤
        const normalizedQuery = debouncedSearchValue.trim().toLowerCase();
        const filteredClusters = clusterOptions.filter(option => 
          option.label.toLowerCase().includes(normalizedQuery)
        );
        
        setSearchResults({
          items: filteredClusters.slice(
            (clusterDropdownPage - 1) * clusterDropdownPageSize,
            clusterDropdownPage * clusterDropdownPageSize
          ),
          total: filteredClusters.length
        });
      } finally {
        setIsSearching(false);
      }
    };

    searchClusters();
  }, [debouncedSearchValue, clusterDropdownPage, clusterOptions, clusterDropdownPageSize]);

  // 处理搜索结果
  const filteredClusterOptions = useMemo(() => {
    if (!searchResults && !clusterSearchValue) {
      return {
        items: clusterOptions.slice(0, clusterDropdownPageSize),
        total: clusterOptions.length
      };
    }

    if (!searchResults) {
      const normalizedQuery = clusterSearchValue.toLowerCase().trim();
      const filteredClusters = clusterOptions.filter(option =>
        option.label.toLowerCase().includes(normalizedQuery)
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

  const handleViewDetails = async (server: ServerWithExtras) => {
    try {
      const serverDetails = await getServerDetails(server.server_id);
      setSelectedServer(transformServerToExtras(serverDetails));
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
              onKeyPress={handleKeyPress}
            />
          </div>
        </form>
        
        <div className="w-full md:w-72">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-full justify-between"
              >
                {clusterFilter === null ? 'All Clusters' : clusterOptions.find(option => option.value === clusterFilter)?.label || 'Select Cluster'}
                <ChevronLeft className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0">
              <Command>
                <CommandInput
                  placeholder="搜索集群（支持名称、标签，支持模糊匹配）..."
                  value={searchValue}
                  onValueChange={(value) => {
                    setSearchValue(value);
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
                          handleClusterFilterChange(null);
                          setOpen(false);
                        }}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>All Clusters</span>
                          <Badge variant="secondary">{clusterOptions.length} servers</Badge>
                        </div>
                      </CommandItem>
                      {filteredClusterOptions.items.map((option: ClusterOption) => (
                        <CommandItem
                          key={option.value}
                          value={option.value}
                          onSelect={() => {
                            handleClusterFilterChange(option.value);
                            setOpen(false);
                          }}
                        >
                          <div className="flex items-center justify-between w-full">
                            <div className="flex flex-col">
                              <span>{option.label}</span>
                            </div>
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
        {servers.slice((page - 1) * pageSize, page * pageSize).map((server) => (
          <ServerCard
            key={server.server_id}
            server={server}
            onClick={() => handleViewDetails(server)}
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
              Page {page} of {totalPages}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
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
  function ServerCard({ server, onClick, score }: ServerCardProps) {
    return (
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
            <span className="truncate">
              {server.cluster_info?.name || 'Uncategorized'}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Wrench className="h-4 w-4" />
            <span>Tools: {server.tool_count}</span>
          </div>
        </CardFooter>
      </Card>
    );
  }
);

export default ServerExplorer;
