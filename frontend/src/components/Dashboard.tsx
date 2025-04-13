import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { Server, EvaluationSummary } from '../types';
import { getServers, evaluateServers, getStatus } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Loader2 } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const Dashboard: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('Checking API status...');
        try {
          const statusResponse = await getStatus();
          if (!statusResponse.has_evaluation) {
            setError('Data is still being processed. Please wait...');
            return;
          }
        } catch (err) {
          console.error('Error checking API status:', err);
          setError('Could not connect to the server. Please try again later.');
          setLoading(false);
          return;
        }
        
        console.log('Fetching dashboard data...');
        const serversData = await getServers({ limit: 1000 });
        setServers(serversData.servers);
        
        const evaluationData = await evaluateServers();
        setEvaluationSummary(evaluationData.evaluation_summary);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
        setLoading(false);
      }
    };

    fetchData();
    
    // 设置定期检查
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const prepareScoreDistributionData = () => {
    if (!evaluationSummary) return [];
    
    return [
      { name: 'Excellent', value: evaluationSummary.score_distribution.excellent },
      { name: 'Good', value: evaluationSummary.score_distribution.good },
      { name: 'Average', value: evaluationSummary.score_distribution.average },
      { name: 'Below Average', value: evaluationSummary.score_distribution.below_average },
      { name: 'Poor', value: evaluationSummary.score_distribution.poor },
    ];
  };

  const prepareAverageScoresData = () => {
    if (!evaluationSummary) return [];
    
    return [
      { name: 'Code Quality', score: evaluationSummary.average_scores.code_quality },
      { name: 'Tool Completeness', score: evaluationSummary.average_scores.tool_completeness },
      { name: 'Documentation', score: evaluationSummary.average_scores.documentation_quality },
      { name: 'Runtime Stability', score: evaluationSummary.average_scores.runtime_stability },
      { name: 'Business Value', score: evaluationSummary.average_scores.business_value },
    ];
  };

  const prepareTopServersData = () => {
    if (!evaluationSummary) return [];
    return evaluationSummary.top_servers.map(server => ({
      name: server.title,
      score: server.score,
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading dashboard data...</span>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Total Servers</CardTitle>
            <CardDescription>Number of MCP servers analyzed</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{servers.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Average Quality Score</CardTitle>
            <CardDescription>Overall quality of MCP servers</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">
              {evaluationSummary ? evaluationSummary.average_scores.overall.toFixed(1) : 'N/A'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Top Server</CardTitle>
            <CardDescription>Highest rated MCP server</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">
              {evaluationSummary && evaluationSummary.top_servers.length > 0
                ? evaluationSummary.top_servers[0].title
                : 'N/A'}
            </div>
            <div className="text-sm text-muted-foreground">
              Score: {evaluationSummary && evaluationSummary.top_servers.length > 0
                ? evaluationSummary.top_servers[0].score.toFixed(1)
                : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="scores">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="scores">Quality Scores</TabsTrigger>
          <TabsTrigger value="distribution">Score Distribution</TabsTrigger>
          <TabsTrigger value="top">Top Servers</TabsTrigger>
        </TabsList>
        
        <TabsContent value="scores" className="p-4 border rounded-md">
          <h3 className="text-lg font-semibold mb-4">Average Quality Scores by Category</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={prepareAverageScoresData()} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} />
              <YAxis dataKey="name" type="category" width={120} />
              <Tooltip formatter={(value) => [`${typeof value === 'number' ? value.toFixed(1) : value}`, 'Score']} />
              <Legend />
              <Bar dataKey="score" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </TabsContent>
        
        <TabsContent value="distribution" className="p-4 border rounded-md">
          <h3 className="text-lg font-semibold mb-4">Server Quality Score Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={prepareScoreDistributionData()}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {prepareScoreDistributionData().map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [value, 'Servers']} />
            </PieChart>
          </ResponsiveContainer>
        </TabsContent>
        
        <TabsContent value="top" className="p-4 border rounded-md">
          <h3 className="text-lg font-semibold mb-4">Top Rated Servers</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={prepareTopServersData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(value) => [`${typeof value === 'number' ? value.toFixed(1) : value}`, 'Score']} />
              <Legend />
              <Bar dataKey="score" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;
