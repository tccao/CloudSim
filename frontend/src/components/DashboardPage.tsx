// =============================================================================
// DashboardPage.tsx
// =============================================================================
// Main dashboard view displaying EC2 instance overview, instance table with
// actions, alarms, zone health, and resource usage summary.
//
// API CALLS:
// - fetchInstances() -> GET /api/ec2/instances
// - deleteInstance() -> DELETE /api/ec2/instances/:id
// - startInstance()  -> POST /api/ec2/instances/:id/start
// - stopInstance()   -> POST /api/ec2/instances/:id/stop
// - rebootInstance() -> POST /api/ec2/instances/:id/reboot
//
// COMPONENT STRUCTURE:
// └── DashboardPage
//     ├── Account Overview Cards (Total, Running, Stopped, Alarms)
//     ├── All Instances Table
//     │   ├── Instance Name (clickable)
//     │   ├── Instance ID, Type, State, Zone, IP, Uptime
//     │   └── Action Buttons (Start/Stop/Reboot/Terminate)
//     ├── Instance Alarms Card
//     ├── Availability Zone Health Card
//     └── Resource Usage Summary Card
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Progress } from './ui/progress';
import { Server, Play, Square, RotateCw, Trash2, AlertTriangle, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { fetchInstances, deleteInstance, startInstance, stopInstance, rebootInstance, type Instance } from '../api/instances';
import { toast } from 'sonner';


// =============================================================================
// TYPES
// =============================================================================

interface DashboardPageProps {
  onInstanceClick: (id: string) => void;
}


// =============================================================================
// CONSTANTS - Mock Data
// =============================================================================

const alarms = [
  { name: 'web-server-01-cpu-high', instance: 'web-server-01', status: 'ok', metric: 'CPU Utilization' },
  { name: 'api-server-01-memory', instance: 'api-server-01', status: 'ok', metric: 'Memory Usage' },
  { name: 'db-server-01-disk', instance: 'db-server-01', status: 'alarm', metric: 'Disk Space' },
  { name: 'dev-server-02-status', instance: 'dev-server-02', status: 'ok', metric: 'Status Check' },
];

const zones = [
  { name: 'us-east-1a', status: 'healthy', instances: 2, cpuAvg: 23 },
  { name: 'us-east-1b', status: 'healthy', instances: 2, cpuAvg: 34 },
  { name: 'us-east-1c', status: 'healthy', instances: 1, cpuAvg: 0 },
];


// =============================================================================
// COMPONENT
// =============================================================================

export function DashboardPage({ onInstanceClick }: DashboardPageProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(true);

  // ---------------------------------------------------------------------------
  // Computed Values
  // ---------------------------------------------------------------------------
  const runningInstances = instances.filter(i => i.state === 'running').length;
  const stoppedInstances = instances.filter(i => i.state === 'stopped').length;
  const totalInstances = instances.length;
  const activeAlarms = alarms.filter(a => a.status === 'alarm').length;

  // ---------------------------------------------------------------------------
  // API Handlers - Load Data
  // ---------------------------------------------------------------------------

  const loadData = async () => {
    try {
      setLoading(true);
      // API CALL: GET /api/ec2/instances
      const data = await fetchInstances();
      setInstances(data);
    } catch (error) {
      console.error('Failed to fetch instances:', error);
      toast.error('Failed to load instances');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ---------------------------------------------------------------------------
  // API Handlers - Instance Actions
  // ---------------------------------------------------------------------------

  const handleDelete = async (id: string) => {
    try {
      // API CALL: DELETE /api/ec2/instances/:id
      await deleteInstance(id);
      toast.success('Instance terminated successfully');
      loadData();
    } catch (error) {
      console.error('Failed to delete instance:', error);
      toast.error('Failed to terminate instance');
    }
  };

  const handleStart = async (id: string) => {
    try {
      // API CALL: POST /api/ec2/instances/:id/start
      await startInstance(id);
      toast.success('Starting instance...');
      loadData();
    } catch (error) {
      console.error('Failed to start instance:', error);
      toast.error('Failed to start instance');
    }
  };

  const handleStop = async (id: string) => {
    try {
      // API CALL: POST /api/ec2/instances/:id/stop
      await stopInstance(id);
      toast.success('Stopping instance...');
      loadData();
    } catch (error) {
      console.error('Failed to stop instance:', error);
      toast.error('Failed to stop instance');
    }
  };

  const handleReboot = async (id: string) => {
    try {
      // API CALL: POST /api/ec2/instances/:id/reboot
      await rebootInstance(id);
      toast.success('Rebooting instance...');
      loadData();
    } catch (error) {
      console.error('Failed to reboot instance:', error);
      toast.error('Failed to reboot instance');
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
  // Render - Main Content
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Account Overview */}
      <div>
        <h2 className="mb-4">Account Overview</h2>
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Server className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Instances</p>
                <p className="text-2xl mt-1">{totalInstances}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <Play className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Running</p>
                <p className="text-2xl mt-1">{runningInstances}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gray-100 rounded-lg">
                <Square className="h-6 w-6 text-gray-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Stopped</p>
                <p className="text-2xl mt-1">{stoppedInstances}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Active Alarms</p>
                <p className="text-2xl mt-1">{activeAlarms}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* All Instances Table */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h3>All Instances</h3>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadData}>
              <RotateCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Instance ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>State</TableHead>
              <TableHead>Zone</TableHead>
              <TableHead>Public IP</TableHead>
              <TableHead>Uptime</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {instances.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center h-24 text-gray-500">
                  No instances found. Launch one!
                </TableCell>
              </TableRow>
            ) : (
              instances.map((instance) => (
                <TableRow key={instance.id}>
                  <TableCell>
                    <button
                      onClick={() => onInstanceClick(instance.id)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                    >
                      {instance.name}
                    </button>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{instance.id}</TableCell>
                  <TableCell>{instance.type}</TableCell>
                  <TableCell>
                    <Badge
                      className={
                        instance.state === 'running'
                          ? 'bg-green-600'
                          : instance.state === 'stopped'
                            ? 'bg-gray-500'
                            : 'bg-yellow-600'
                      }
                    >
                      {instance.state}
                    </Badge>
                  </TableCell>
                  <TableCell>{instance.zone}</TableCell>
                  <TableCell className="font-mono text-xs">{instance.publicIp}</TableCell>
                  <TableCell>{instance.uptime}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {instance.state === 'stopped' ? (
                        <Button variant="ghost" size="sm" title="Start" onClick={() => handleStart(instance.id)}>
                          <Play className="h-4 w-4 text-green-600" />
                        </Button>
                      ) : (
                        <>
                          <Button variant="ghost" size="sm" title="Stop" onClick={() => handleStop(instance.id)}>
                            <Square className="h-4 w-4 text-gray-600" />
                          </Button>
                          <Button variant="ghost" size="sm" title="Reboot" onClick={() => handleReboot(instance.id)}>
                            <RotateCw className="h-4 w-4 text-blue-600" />
                          </Button>
                        </>
                      )}
                      <Button variant="ghost" size="sm" title="Terminate" onClick={() => handleDelete(instance.id)}>
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Two Column Layout: Alarms + Zone Health */}
      <div className="grid grid-cols-2 gap-6">
        {/* Instance Alarms */}
        <Card className="p-6">
          <h3 className="mb-4">Instance Alarms</h3>

          <div className="space-y-3">
            {alarms.map((alarm, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {alarm.status === 'ok' ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  <div>
                    <p className="text-sm">{alarm.name}</p>
                    <p className="text-xs text-gray-600">
                      {alarm.instance} • {alarm.metric}
                    </p>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={
                    alarm.status === 'ok'
                      ? 'border-green-500 text-green-700'
                      : 'border-red-500 text-red-700'
                  }
                >
                  {alarm.status.toUpperCase()}
                </Badge>
              </div>
            ))}
          </div>

          <Button variant="outline" className="w-full mt-4" size="sm">
            View All Alarms
          </Button>
        </Card>

        {/* Zone Health */}
        <Card className="p-6">
          <h3 className="mb-4">Availability Zone Health</h3>

          <div className="space-y-4">
            {zones.map((zone, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span>{zone.name}</span>
                    {zone.status === 'healthy' ? (
                      <Badge variant="outline" className="border-green-500 text-green-700">
                        Healthy
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-yellow-500 text-yellow-700">
                        Degraded
                      </Badge>
                    )}
                  </div>
                  <span className="text-sm text-gray-600">{zone.instances} instances</span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-600">
                    <span>Avg CPU: {zone.cpuAvg}%</span>
                    <span>{zone.cpuAvg}%</span>
                  </div>
                  <Progress value={zone.cpuAvg} className="h-2" />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <p className="text-sm">All zones operational</p>
                <p className="text-xs text-gray-600 mt-1">
                  Last checked: 2 minutes ago
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Resource Usage Summary */}
      <Card className="p-6">
        <h3 className="mb-4">Resource Usage Summary</h3>

        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600">vCPU Usage</span>
              <span className="text-sm">7 / 20</span>
            </div>
            <Progress value={35} className="h-2" />
            <p className="text-xs text-gray-600 mt-1">35% of account limit</p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600">Memory (GiB)</span>
              <span className="text-sm">15 / 64</span>
            </div>
            <Progress value={23} className="h-2" />
            <p className="text-xs text-gray-600 mt-1">23% of account limit</p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600">EBS Storage (GB)</span>
              <span className="text-sm">180 / 1000</span>
            </div>
            <Progress value={18} className="h-2" />
            <p className="text-xs text-gray-600 mt-1">18% of account limit</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
