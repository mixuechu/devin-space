import React, { useState, useEffect, useCallback } from 'react';
import { SearchResult, UserPreferences, searchServers, getRecommendations, getPersonalizedRecommendations, getServerDetails } from '../services/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Loader2, Search, Tag, ThumbsUp, Sparkles, ExternalLink } from 'lucide-react';
import { Slider } from './ui/slider';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from './ui/dialog';

// Debounce helper function
const debounce = <F extends (...args: any[]) => any>(
  func: F,
  waitFor: number
) => {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<F>): void => {
    if (timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), waitFor);
  };
};

const RecommendationView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');
  const [recommendations, setRecommendations] = useState<SearchResult[]>([]);
  const [personalizedRecommendations, setPersonalizedRecommendations] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('search');
  const [selectedServer, setSelectedServer] = useState<any>(null);
  const [detailsOpen, setDetailsOpen] = useState<boolean>(false);
  const [detailsLoading, setDetailsLoading] = useState<boolean>(false);
  
  const [userPreferences, setUserPreferences] = useState<UserPreferences>({
    weights: {
      code_quality: 1.0,
      tool_completeness: 1.0,
      documentation_quality: 1.0,
      runtime_stability: 1.0,
      business_value: 1.0,
    },
    preferred_tags: [],
  });
  
  const [preferredTag, setPreferredTag] = useState<string>('');

  // Debounced search handler
  const debouncedSetSearch = useCallback(
    debounce((value: string) => {
      setDebouncedQuery(value);
    }, 300),
    []
  );

  // Handle input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    debouncedSetSearch(value);
  };

  // Effect to handle search when debounced query changes
  useEffect(() => {
    if (debouncedQuery) {
      handleSearch();
    }
  }, [debouncedQuery]);

  const handleSearch = async () => {
    if (!debouncedQuery.trim()) return;
    
    try {
      setLoading(true);
      setError(null);
      
      console.log('Searching for recommendations with query:', debouncedQuery);
      
      try {
        const searchResponse = await searchServers(debouncedQuery, 5);
        
        if (searchResponse.results && searchResponse.results.length > 0) {
          setRecommendations(searchResponse.results);
        } else {
          const recommendResponse = await getRecommendations(debouncedQuery, 5);
          
          if (recommendResponse.recommendations && recommendResponse.recommendations.length > 0) {
            setRecommendations(recommendResponse.recommendations.map((rec: any) => ({
              ...rec,
              is_ai_recommendation: true
            })));
          } else {
            setRecommendations([]);
          }
        }
      } catch (error) {
        console.error('API request failed:', error);
        throw error;
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error getting recommendations:', err);
      setError('Failed to get recommendations. Please try again later.');
      setLoading(false);
    }
  };

  const handlePersonalizedRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Getting personalized recommendations with preferences:', userPreferences);
      
      const response = await getPersonalizedRecommendations(userPreferences, 5);
      
      if (response.recommendations && response.recommendations.length > 0) {
        setPersonalizedRecommendations(response.recommendations);
      } else {
        setPersonalizedRecommendations([]);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error getting personalized recommendations:', err);
      setError('Failed to get personalized recommendations. Please try again later.');
      setLoading(false);
    }
  };

  const handleWeightChange = (category: keyof UserPreferences['weights'], value: number[]) => {
    setUserPreferences(prev => ({
      ...prev,
      weights: {
        ...prev.weights,
        [category]: value[0],
      },
    }));
  };

  const addPreferredTag = () => {
    if (!preferredTag.trim()) return;
    
    setUserPreferences(prev => ({
      ...prev,
      preferred_tags: [...prev.preferred_tags, preferredTag.trim()],
    }));
    
    setPreferredTag('');
  };

  const removePreferredTag = (tag: string) => {
    setUserPreferences(prev => ({
      ...prev,
      preferred_tags: prev.preferred_tags.filter(t => t !== tag),
    }));
  };
  
  const handleViewDetails = async (serverId: string) => {
    try {
      setDetailsLoading(true);
      console.log('Fetching details for server:', serverId);
      
      const serverDetails = await getServerDetails(serverId);
      console.log('Server details received:', serverDetails);
      
      setSelectedServer(serverDetails);
      setDetailsOpen(true);
      setDetailsLoading(false);
    } catch (err) {
      console.error('Error fetching server details:', err);
      setError('Failed to load server details. Please try again later.');
      setDetailsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="search">Search Recommendations</TabsTrigger>
          <TabsTrigger value="personalized">Personalized Recommendations</TabsTrigger>
        </TabsList>
        
        <TabsContent value="search" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search for Server Recommendations</CardTitle>
              <CardDescription>
                Enter a search query to get server recommendations based on your needs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <div className="relative flex-grow">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search for servers..."
                    className="pl-8"
                    value={searchQuery}
                    onChange={handleSearchChange}
                  />
                </div>
                <Button onClick={handleSearch} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>

          {error && (
            <div className="bg-red-50 p-4 rounded-md text-red-800">
              <p>{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {recommendations.length > 0 ? (
              recommendations.map((result) => (
                <Card key={result.id} className="flex flex-col h-full">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg">{result.title}</CardTitle>
                      {result.quality_score && (
                        <Badge variant="outline" className="ml-2">
                          Score: {Math.round(result.quality_score)}
                        </Badge>
                      )}
                    </div>
                    <CardDescription>{result.description}</CardDescription>
                  </CardHeader>
                  
                  <CardContent className="flex-grow">
                    <div className="flex flex-wrap gap-2 mb-4">
                      {result.tags.map((tag, index) => (
                        <Badge key={index} variant="secondary" className="flex items-center gap-1">
                          <Tag className="h-3 w-3" />
                          {tag.replace(/^#\s*/, '')}
                        </Badge>
                      ))}
                    </div>
                    
                    <div className="flex items-center gap-2 text-sm">
                      <ThumbsUp className="h-4 w-4 text-muted-foreground" />
                      <span>Relevance: {result.relevance_score.toFixed(1)}</span>
                    </div>
                    
                    {result.is_ai_recommendation && (
                      <div className="mt-2 flex items-center gap-2 text-sm text-purple-600">
                        <Sparkles className="h-4 w-4" />
                        <span>AI Recommendation</span>
                      </div>
                    )}
                  </CardContent>
                  
                  <CardFooter className="border-t pt-4">
                    <Button 
                      variant="outline" 
                      className="w-full"
                      onClick={() => handleViewDetails(result.id)}
                      disabled={detailsLoading}
                    >
                      {detailsLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                      View Details
                    </Button>
                  </CardFooter>
                </Card>
              ))
            ) : (
              !loading && (
                <div className="col-span-full text-center py-12">
                  <p className="text-muted-foreground">
                    {searchQuery.trim()
                      ? 'No recommendations found. Try a different search query.'
                      : 'Enter a search query to get recommendations.'}
                  </p>
                </div>
              )
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="personalized" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Personalized Recommendations</CardTitle>
              <CardDescription>
                Customize your preferences to get personalized server recommendations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <Label className="text-base">Code Quality</Label>
                  <Slider
                    defaultValue={[1.0]}
                    max={2}
                    step={0.1}
                    value={[userPreferences.weights.code_quality]}
                    onValueChange={(value) => handleWeightChange('code_quality', value)}
                    className="mt-2"
                  />
                </div>
                
                <div>
                  <Label className="text-base">Tool Completeness</Label>
                  <Slider
                    defaultValue={[1.0]}
                    max={2}
                    step={0.1}
                    value={[userPreferences.weights.tool_completeness]}
                    onValueChange={(value) => handleWeightChange('tool_completeness', value)}
                    className="mt-2"
                  />
                </div>
                
                <div>
                  <Label className="text-base">Documentation Quality</Label>
                  <Slider
                    defaultValue={[1.0]}
                    max={2}
                    step={0.1}
                    value={[userPreferences.weights.documentation_quality]}
                    onValueChange={(value) => handleWeightChange('documentation_quality', value)}
                    className="mt-2"
                  />
                </div>
                
                <div>
                  <Label className="text-base">Runtime Stability</Label>
                  <Slider
                    defaultValue={[1.0]}
                    max={2}
                    step={0.1}
                    value={[userPreferences.weights.runtime_stability]}
                    onValueChange={(value) => handleWeightChange('runtime_stability', value)}
                    className="mt-2"
                  />
                </div>
                
                <div>
                  <Label className="text-base">Business Value</Label>
                  <Slider
                    defaultValue={[1.0]}
                    max={2}
                    step={0.1}
                    value={[userPreferences.weights.business_value]}
                    onValueChange={(value) => handleWeightChange('business_value', value)}
                    className="mt-2"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label className="text-base">Preferred Tags</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add a preferred tag..."
                    value={preferredTag}
                    onChange={(e) => setPreferredTag(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addPreferredTag()}
                  />
                  <Button variant="outline" onClick={addPreferredTag}>
                    Add
                  </Button>
                </div>
                
                <div className="flex flex-wrap gap-2 mt-2">
                  {userPreferences.preferred_tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      {tag}
                      <button
                        onClick={() => removePreferredTag(tag)}
                        className="ml-1 h-3 w-3 rounded-full bg-muted-foreground/20 flex items-center justify-center hover:bg-muted-foreground/40"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
              
              <Button onClick={handlePersonalizedRecommendations} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Get Personalized Recommendations
              </Button>
            </CardContent>
          </Card>

          {error && (
            <div className="bg-red-50 p-4 rounded-md text-red-800">
              <p>{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {personalizedRecommendations.length > 0 ? (
              personalizedRecommendations.map((result) => (
                <Card key={result.id} className="flex flex-col h-full">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg">{result.title}</CardTitle>
                      <Badge variant="outline" className="ml-2">
                        Score: {result.personalized_score ? Math.round(result.personalized_score) : 'N/A'}
                      </Badge>
                    </div>
                    <CardDescription>{result.description}</CardDescription>
                  </CardHeader>
                  
                  <CardContent className="flex-grow">
                    <div className="flex flex-wrap gap-2 mb-4">
                      {result.tags.map((tag, index) => (
                        <Badge key={index} variant="secondary" className="flex items-center gap-1">
                          <Tag className="h-3 w-3" />
                          {tag.replace(/^#\s*/, '')}
                        </Badge>
                      ))}
                    </div>
                    
                    {result.quality_scores && (
                      <div className="space-y-1 text-sm">
                        <p>Code Quality: {result.quality_scores.code_quality.toFixed(1)}</p>
                        <p>Tool Completeness: {result.quality_scores.tool_completeness.toFixed(1)}</p>
                        <p>Documentation: {result.quality_scores.documentation_quality.toFixed(1)}</p>
                        <p>Runtime Stability: {result.quality_scores.runtime_stability.toFixed(1)}</p>
                        <p>Business Value: {result.quality_scores.business_value.toFixed(1)}</p>
                      </div>
                    )}
                  </CardContent>
                  
                  <CardFooter className="border-t pt-4">
                    <Button 
                      variant="outline" 
                      className="w-full"
                      onClick={() => handleViewDetails(result.id)}
                      disabled={detailsLoading}
                    >
                      {detailsLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                      View Details
                    </Button>
                  </CardFooter>
                </Card>
              ))
            ) : (
              !loading && (
                <div className="col-span-full text-center py-12">
                  <p className="text-muted-foreground">
                    Set your preferences and click "Get Personalized Recommendations" to see results.
                  </p>
                </div>
              )
            )}
          </div>
        </TabsContent>
      </Tabs>
      
      {/* Server Details Modal */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          {selectedServer ? (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl flex items-center justify-between">
                  {selectedServer.title}
                  <Badge variant="outline" className="ml-2">
                    Score: {selectedServer.overall_score ? Math.round(selectedServer.overall_score) : 'N/A'}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-base">{selectedServer.description}</DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                <div className="flex flex-wrap gap-2 mb-4">
                  {selectedServer.tags && selectedServer.tags.map((tag: string, index: number) => (
                    <Badge key={index} variant="secondary" className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      {tag.replace(/^#\s*/, '')}
                    </Badge>
                  ))}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Quality Scores</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {selectedServer.code_quality_score !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Code Quality:</span>
                          <span className="font-medium">{selectedServer.code_quality_score.toFixed(1)}</span>
                        </div>
                      )}
                      {selectedServer.tool_completeness_score !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Tool Completeness:</span>
                          <span className="font-medium">{selectedServer.tool_completeness_score.toFixed(1)}</span>
                        </div>
                      )}
                      {selectedServer.documentation_quality_score !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Documentation Quality:</span>
                          <span className="font-medium">{selectedServer.documentation_quality_score.toFixed(1)}</span>
                        </div>
                      )}
                      {selectedServer.runtime_stability_score !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Runtime Stability:</span>
                          <span className="font-medium">{selectedServer.runtime_stability_score.toFixed(1)}</span>
                        </div>
                      )}
                      {selectedServer.business_value_score !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Business Value:</span>
                          <span className="font-medium">{selectedServer.business_value_score.toFixed(1)}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Server Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {selectedServer.word_count !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Word Count:</span>
                          <span className="font-medium">{selectedServer.word_count}</span>
                        </div>
                      )}
                      {selectedServer.tool_count !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Tools:</span>
                          <span className="font-medium">{selectedServer.tool_count}</span>
                        </div>
                      )}
                      {selectedServer.has_github !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>GitHub:</span>
                          <span className="font-medium">{selectedServer.has_github ? 'Yes' : 'No'}</span>
                        </div>
                      )}
                      {selectedServer.has_faq !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>FAQ:</span>
                          <span className="font-medium">{selectedServer.has_faq ? 'Yes' : 'No'}</span>
                        </div>
                      )}
                      {selectedServer.cluster_id !== undefined && (
                        <div className="flex justify-between items-center">
                          <span>Cluster:</span>
                          <span className="font-medium">{selectedServer.cluster_id}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
                
                {selectedServer.page_url && (
                  <div className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    <a 
                      href={selectedServer.page_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Project Page
                    </a>
                  </div>
                )}
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setDetailsOpen(false)}>
                  Close
                </Button>
              </DialogFooter>
            </>
          ) : (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-2">Loading server details...</span>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RecommendationView;
