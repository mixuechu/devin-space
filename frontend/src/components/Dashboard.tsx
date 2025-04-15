import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { Server, EvaluationSummary } from '../types';
import { getServers, evaluateServers, getStatus } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { staticData } from '../store/dataCache';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

interface GetServersResponse {
  servers: Server[];
  total: number;
}

const Dashboard: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async (forceRefresh = false) => {
    try {
      // 如果不是强制刷新且有有效缓存，直接使用缓存数据
      if (!forceRefresh && staticData.hasValidCache()) {
        const cachedServers = staticData.getServers();
        const cachedEvaluation = staticData.getEvaluation();
        
        if (cachedServers && cachedEvaluation) {
          setServers(cachedServers.servers);
          setEvaluationSummary(cachedEvaluation);
          setLoading(false);
          return;
        }
      }

      setLoading(true);
      setError(null);
      console.log('Fetching dashboard data from API...');

      const [serversResponse, evaluationResponse] = await Promise.all([
        getServers(),
        evaluateServers()
      ]);

      if (serversResponse) {
        const serverData = serversResponse as GetServersResponse;
        staticData.setServers(serverData);
        setServers(serverData.servers);
      }

      if (evaluationResponse?.evaluation_summary) {
        const evaluationData = evaluationResponse.evaluation_summary;
        staticData.setEvaluation(evaluationData);
        setEvaluationSummary(evaluationData);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to fetch dashboard data. Please try again later.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
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
      <div className="flex items-center justify-center h-[200px]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 text-center p-4">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        
        {process.env.NODE_ENV === 'development' && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              staticData.clearAll();
              fetchDashboardData(true);
            }}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Force Refresh
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Total Servers</CardTitle>
            <CardDescription>Number of servers in the system</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{servers.length}</p>
          </CardContent>
        </Card>

        {evaluationSummary && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Average Score</CardTitle>
                <CardDescription>Mean performance score</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {evaluationSummary.average_scores.overall.toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>High Performers</CardTitle>
                <CardDescription>Servers with score {'>'} 0.8</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {evaluationSummary.top_servers.length}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Low Performers</CardTitle>
                <CardDescription>Servers with score {'<'} 0.5</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {servers.filter(server => (server.overall_score || 0) < 0.5).length}
                </p>
              </CardContent>
            </Card>
          </>
        )}
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
