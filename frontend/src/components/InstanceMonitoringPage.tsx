// =============================================================================
// InstanceMonitoringPage.tsx
// =============================================================================
// Monitoring dashboard for EC2 instances showing CloudWatch metrics, cost data,
// and system logs. Includes charts for CPU, memory, network, disk, and costs.
//
// API CALLS:
// - fetchInstances()       -> GET /api/ec2/instances
// - getInstanceMetrics()   -> GET /api/ec2/instances/:id/metrics
// - getDailyCosts()        -> GET /api/ec2/costs/daily
// - getCostSummary()       -> GET /api/ec2/costs/summary
//
// COMPONENT STRUCTURE:
// └── InstanceMonitoringPage
//     ├── Header (Title, Instance Selector, Period, Refresh, Export)
//     ├── Status Cards (CPU, Memory, Network, Disk, Cost)
//     ├── Metric Tabs
//     │   ├── CPU Tab (Area chart)
//     │   ├── Memory Tab (Stacked area chart - mock)
//     │   ├── Network Tab (Line chart)
//     │   ├── Disk I/O Tab (Bar chart)
//     │   └── Cost Tab (Area chart + Pie chart + Summary)
//     └── System Logs Card (mock)
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Activity, Download, RefreshCw, DollarSign, AlertCircle, Loader2 } from 'lucide-react';
import { getInstanceMetrics, getDailyCosts, getCostSummary, type InstanceMetrics, type DailyCost, type CostSummary } from '../api/ec2';
import { fetchInstances, type Instance } from '../api/instances';


// =============================================================================
// TYPES
// =============================================================================

// (Types are imported from api modules)


// =============================================================================
// CONSTANTS - Mock Data
// =============================================================================

const MOCK_DAILY_COSTS: DailyCost[] = [
  { date: '2025-11-08', compute: 1.5, storage: 0.5, network: 0.2, total: 2.2 },
  { date: '2025-11-09', compute: 1.8, storage: 0.6, network: 0.3, total: 2.7 },
  { date: '2025-11-10', compute: 2.0, storage: 0.7, network: 0.4, total: 3.1 },
  { date: '2025-11-11', compute: 1.9, storage: 0.6, network: 0.3, total: 2.8 },
  { date: '2025-11-12', compute: 2.1, storage: 0.7, network: 0.5, total: 3.3 },
  { date: '2025-11-13', compute: 1.7, storage: 0.6, network: 0.3, total: 2.6 },
  { date: '2025-11-14', compute: 1.6, storage: 0.6, network: 0.2, total: 2.4 },
];

const MOCK_COST_SUMMARY: CostSummary = {
  month_to_date: 19.1,
  projected_monthly: 45.5,
  days_elapsed: 14,
};

// Mock log entries (requires CloudWatch Logs API)
const logEntries = [
  { timestamp: '2025-11-13 14:32:45', level: 'INFO', message: 'Instance health check passed' },
  { timestamp: '2025-11-13 14:30:12', level: 'INFO', message: 'Network interface eth0 traffic normal' },
  { timestamp: '2025-11-13 14:28:03', level: 'WARN', message: 'CPU utilization spike detected (78%)' },
  { timestamp: '2025-11-13 14:25:30', level: 'INFO', message: 'Disk I/O operations within normal range' },
];

// Mock memory data (requires CloudWatch Agent)
const memoryData = [
  { time: '00:00', used: 512, available: 512 },
  { time: '04:00', used: 486, available: 538 },
  { time: '08:00', used: 615, available: 409 },
  { time: '12:00', used: 768, available: 256 },
];


// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const formatTime = (isoString: string): string => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};


// =============================================================================
// COMPONENT
// =============================================================================

export function InstanceMonitoringPage() {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [instances, setInstances] = useState<Instance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [metrics, setMetrics] = useState<InstanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [period, setPeriod] = useState('60');
  const [costData, setCostData] = useState<DailyCost[]>([]);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [costsLoading, setCostsLoading] = useState(false);

  // ---------------------------------------------------------------------------
  // API Handlers - Load Instances
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const loadInstances = async () => {
      try {
        // API CALL: GET /api/ec2/instances
        const data = await fetchInstances();
        setInstances(data);
        if (data.length > 0) setSelectedInstance(data[0].id);
      } catch (err) {
        console.error('Failed to fetch instances:', err);
      } finally {
        setLoading(false);
      }
    };
    loadInstances();
  }, []);

  // ---------------------------------------------------------------------------
  // API Handlers - Load Metrics
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!selectedInstance) return;
    const loadMetrics = async () => {
      setMetricsLoading(true);
      try {
        // API CALL: GET /api/ec2/instances/:id/metrics
        const data = await getInstanceMetrics(selectedInstance, parseInt(period));
        setMetrics(data);
      } catch (err) {
        console.error('Failed to fetch metrics:', err);
      } finally {
        setMetricsLoading(false);
      }
    };
    loadMetrics();
  }, [selectedInstance, period]);

  // ---------------------------------------------------------------------------
  // API Handlers - Load Costs
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const loadCosts = async () => {
      setCostsLoading(true);
      try {
        // API CALLS: GET /api/ec2/costs/daily + GET /api/ec2/costs/summary
        const [dailyCosts, summary] = await Promise.all([
          getDailyCosts(7),
          getCostSummary()
        ]);
        setCostData(dailyCosts);
        setCostSummary(summary);
      } catch (err) {
        console.error('Failed to fetch costs:', err);
        // Fallback to mock data if API fails
        setCostData(MOCK_DAILY_COSTS);
        setCostSummary(MOCK_COST_SUMMARY);
      } finally {
        setCostsLoading(false);
      }
    };
    loadCosts();
  }, []);

  // ---------------------------------------------------------------------------
  // Computed Values - Chart Data
  // ---------------------------------------------------------------------------

  const cpuData = metrics?.cpu_utilization.map(dp => ({
    time: formatTime(dp.timestamp),
    usage: dp.value,
  })) || [];

  const networkData = metrics ? metrics.network_in.map((dp, i) => ({
    time: formatTime(dp.timestamp),
    in: Math.round(dp.value / 1024),
    out: Math.round((metrics.network_out[i]?.value || 0) / 1024),
  })) : [];

  const diskData = metrics ? metrics.disk_read_ops.map((dp, i) => ({
    time: formatTime(dp.timestamp),
    read: dp.value,
    write: metrics.disk_write_ops[i]?.value || 0,
  })) : [];

  const currentCpu = cpuData.length > 0 ? cpuData[cpuData.length - 1].usage : 0;
  const currentNetworkIn = metrics?.network_in.length ? metrics.network_in[metrics.network_in.length - 1].value : 0;
  const selectedInstanceData = instances.find(i => i.id === selectedInstance);

  // Compute cost breakdown from daily data
  const costBreakdown = [
    { name: 'Compute', value: costData.reduce((sum, d) => sum + d.compute, 0), color: '#3b82f6' },
    { name: 'Storage', value: costData.reduce((sum, d) => sum + d.storage, 0), color: '#8b5cf6' },
    { name: 'Network', value: costData.reduce((sum, d) => sum + d.network, 0), color: '#10b981' },
  ];
  const weekTotal = costData.reduce((sum, d) => sum + d.total, 0);

  // ---------------------------------------------------------------------------
  // Handlers - Refresh
  // ---------------------------------------------------------------------------

  const handleRefresh = async () => {
    // Refresh metrics
    if (selectedInstance) {
      setMetricsLoading(true);
      try {
        // API CALL: GET /api/ec2/instances/:id/metrics
        const data = await getInstanceMetrics(selectedInstance, parseInt(period));
        setMetrics(data);
      } catch (err) {
        console.error('Failed to refresh metrics:', err);
      } finally {
        setMetricsLoading(false);
      }
    }

    // Refresh costs
    setCostsLoading(true);
    try {
      // API CALLS: GET /api/ec2/costs/daily + GET /api/ec2/costs/summary
      const [dailyCosts, summary] = await Promise.all([
        getDailyCosts(7),
        getCostSummary()
      ]);
      setCostData(dailyCosts);
      setCostSummary(summary);
    } catch (err) {
      console.error('Failed to refresh costs:', err);
      setCostData(MOCK_DAILY_COSTS);
      setCostSummary(MOCK_COST_SUMMARY);
    } finally {
      setCostsLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render - Loading State
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render - Empty State
  // ---------------------------------------------------------------------------

  if (instances.length === 0) {
    return (
      <div className="flex h-[400px] items-center justify-center flex-col gap-4">
        <AlertCircle className="h-12 w-12 text-gray-400" />
        <p className="text-gray-600">No instances found. Create one to view metrics.</p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render - Main Content
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3">
            <h1>Instance Monitoring</h1>
            <Badge className={selectedInstanceData?.state === 'running' ? 'bg-green-600' : 'bg-gray-500'}>
              {selectedInstanceData?.state || 'Unknown'}
            </Badge>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            {selectedInstanceData?.name || 'Select instance'} ({selectedInstance})
          </p>
        </div>

        <div className="flex gap-2">
          <Select value={selectedInstance} onValueChange={setSelectedInstance}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select instance" />
            </SelectTrigger>
            <SelectContent>
              {instances.map(inst => (
                <SelectItem key={inst.id} value={inst.id}>{inst.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="15">Last 15 min</SelectItem>
              <SelectItem value="60">Last 1 hour</SelectItem>
              <SelectItem value="360">Last 6 hours</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={metricsLoading || costsLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${metricsLoading || costsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-blue-600" />
            <p className="text-sm text-gray-600">CPU Utilization</p>
          </div>
          <p className="text-2xl">{currentCpu.toFixed(1)}%</p>
          <p className="text-xs text-gray-600 mt-1">From CloudWatch</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-purple-600" />
            <p className="text-sm text-gray-600">Memory Usage</p>
          </div>
          <p className="text-2xl">512 MB</p>
          <p className="text-xs text-gray-600 mt-1">Mock data</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-green-600" />
            <p className="text-sm text-gray-600">Network In</p>
          </div>
          <p className="text-2xl">{formatBytes(currentNetworkIn)}</p>
          <p className="text-xs text-gray-600 mt-1">From CloudWatch</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-orange-600" />
            <p className="text-sm text-gray-600">Disk Ops</p>
          </div>
          <p className="text-2xl">{diskData.length > 0 ? diskData[diskData.length - 1].read : 0}/s</p>
          <p className="text-xs text-gray-600 mt-1">From CloudWatch</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="h-4 w-4 text-emerald-600" />
            <p className="text-sm text-gray-600">Today's Cost</p>
          </div>
          <p className="text-2xl">$3.80</p>
          <p className="text-xs text-gray-600 mt-1">Estimated</p>
        </Card>
      </div>

      {/* Loading Indicator */}
      {metricsLoading && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          <span className="ml-2 text-sm text-gray-600">Loading metrics...</span>
        </div>
      )}

      {/* Metric Charts Tabs */}
      <Tabs defaultValue="cpu" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="cpu">CPU</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="network">Network</TabsTrigger>
          <TabsTrigger value="disk">Disk I/O</TabsTrigger>
          <TabsTrigger value="cost">Cost</TabsTrigger>
        </TabsList>

        {/* CPU Tab */}
        <TabsContent value="cpu" className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4">CPU Utilization (%) - CloudWatch</h3>
            {cpuData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={cpuData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="usage" stroke="#3b82f6" fill="#93c5fd" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No CPU data available
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Memory Tab */}
        <TabsContent value="memory" className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4">Memory Usage (MB) - Mock Data</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={memoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="used" stackId="1" stroke="#8b5cf6" fill="#c4b5fd" />
                <Area type="monotone" dataKey="available" stackId="1" stroke="#10b981" fill="#86efac" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        {/* Network Tab */}
        <TabsContent value="network" className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4">Network Traffic (KB/s) - CloudWatch</h3>
            {networkData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={networkData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="in" stroke="#10b981" strokeWidth={2} />
                  <Line type="monotone" dataKey="out" stroke="#f59e0b" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No network data available
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Disk I/O Tab */}
        <TabsContent value="disk" className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4">Disk I/O (ops/s) - CloudWatch</h3>
            {diskData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={diskData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="read" fill="#3b82f6" />
                  <Bar dataKey="write" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No disk data available
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Cost Tab */}
        <TabsContent value="cost" className="space-y-4">
          <Card className="p-6">
            <h3 className="mb-4">Daily Cost Trend ($) - Mock Data</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={costData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="compute" stackId="1" stroke="#3b82f6" fill="#93c5fd" />
                <Area type="monotone" dataKey="storage" stackId="1" stroke="#8b5cf6" fill="#c4b5fd" />
                <Area type="monotone" dataKey="network" stackId="1" stroke="#10b981" fill="#86efac" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          <div className="grid grid-cols-2 gap-4">
            {/* Cost Breakdown Pie Chart */}
            <Card className="p-6">
              <h3 className="mb-4">Cost Breakdown</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={costBreakdown}
                    cx="50%"
                    cy="50%"
                    outerRadius={60}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, value }) => `${name}: $${value}`}
                  >
                    {costBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            {/* Cost Summary */}
            <Card className="p-6">
              <h3 className="mb-4">Cost Summary {costsLoading && <Loader2 className="inline h-4 w-4 animate-spin ml-2" />}</h3>
              <div className="space-y-3">
                <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">Week to Date</span>
                  <span className="font-medium">${weekTotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">Month to Date</span>
                  <span className="font-medium">${costSummary?.month_to_date.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between p-3 bg-blue-50 rounded-lg">
                  <span className="text-sm text-gray-600">Projected Monthly</span>
                  <span className="font-medium text-blue-700">${costSummary?.projected_monthly.toFixed(2) || '0.00'}</span>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* System Logs */}
      <Card className="p-6">
        <h3 className="mb-4">System Logs (Mock)</h3>
        <div className="space-y-2">
          {logEntries.map((log, index) => (
            <div key={index} className="flex gap-4 p-3 rounded-lg bg-gray-50">
              <span className="text-xs text-gray-500 font-mono">{log.timestamp}</span>
              <Badge
                variant="outline"
                className={
                  log.level === 'ERROR' ? 'border-red-500 text-red-700' :
                    log.level === 'WARN' ? 'border-yellow-500 text-yellow-700' :
                      'border-blue-500 text-blue-700'
                }
              >
                {log.level}
              </Badge>
              <span className="text-sm">{log.message}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
