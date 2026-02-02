// =============================================================================
// ScalingConfigDialog.tsx
// =============================================================================
// Configuration dialog for instance compute resources and advanced settings.
// Allows users to adjust instance type, CPU/memory allocation, storage, and
// behavior settings.
//
// API CALLS: None (local state only, mock save)
//
// COMPONENT STRUCTURE:
// └── ScalingConfigDialog
//     ├── Header (Instance name, description)
//     ├── Tabs
//     │   ├── Compute Resources Tab
//     │   │   ├── Dynamic Scaling Toggle
//     │   │   ├── Instance Type Select
//     │   │   ├── CPU Allocation Slider
//     │   │   ├── Memory Allocation Slider
//     │   │   └── Estimated Cost Card
//     │   └── Advanced Settings Tab
//     │       ├── Storage Configuration
//     │       └── Instance Behavior Settings
//     └── Footer (Cancel/Save buttons)
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Card } from './ui/card';
import { Separator } from './ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Slider } from './ui/slider';
import { Cpu, HardDrive, Zap, Settings as SettingsIcon } from 'lucide-react';


// =============================================================================
// TYPES
// =============================================================================

interface ScalingConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instanceName?: string;
}


// =============================================================================
// COMPONENT
// =============================================================================

export function ScalingConfigDialog({ open, onOpenChange, instanceName = 'web-server-01' }: ScalingConfigDialogProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [cpuAllocation, setCpuAllocation] = useState([75]);
  const [memoryAllocation, setMemoryAllocation] = useState([3]);
  const [instanceType, setInstanceType] = useState('t3.medium');

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleSave = () => {
    // Mock save - in production, this would call an API
    alert(`Configuration saved for ${instanceName}:\nInstance Type: ${instanceType}\nCPU: ${cpuAllocation[0]}%\nMemory: ${memoryAllocation[0]}GB`);
    onOpenChange(false);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Instance: {instanceName}</DialogTitle>
          <DialogDescription>
            Adjust compute resources and configuration settings for this instance
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="compute" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="compute">Compute Resources</TabsTrigger>
            <TabsTrigger value="settings">Advanced Settings</TabsTrigger>
          </TabsList>

          {/* Compute Resources Tab */}
          <TabsContent value="compute" className="space-y-4 mt-4">
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="h-5 w-5 text-blue-600" />
                <h3 className="font-medium">Compute Scaling</h3>
              </div>

              <div className="space-y-4">
                {/* Dynamic Scaling Toggle */}
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Dynamic Scaling Enabled</Label>
                    <p className="text-sm text-gray-600">Adjust compute resources based on workload</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                {/* Instance Type Select */}
                <div className="space-y-2">
                  <Label htmlFor="instance-type">Instance Type</Label>
                  <Select value={instanceType} onValueChange={setInstanceType}>
                    <SelectTrigger id="instance-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="t3.micro">t3.micro (2 vCPU, 1GB RAM) - $0.010/hr</SelectItem>
                      <SelectItem value="t3.small">t3.small (2 vCPU, 2GB RAM) - $0.021/hr</SelectItem>
                      <SelectItem value="t3.medium">t3.medium (2 vCPU, 4GB RAM) - $0.042/hr</SelectItem>
                      <SelectItem value="t3.large">t3.large (2 vCPU, 8GB RAM) - $0.083/hr</SelectItem>
                      <SelectItem value="t3.xlarge">t3.xlarge (4 vCPU, 16GB RAM) - $0.166/hr</SelectItem>
                      <SelectItem value="t3.2xlarge">t3.2xlarge (8 vCPU, 32GB RAM) - $0.332/hr</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-500">Select instance type based on your workload requirements</p>
                </div>

                {/* CPU Allocation Slider */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>CPU Allocation</Label>
                    <span className="text-sm font-medium">{cpuAllocation[0]}%</span>
                  </div>
                  <Slider
                    value={cpuAllocation}
                    onValueChange={setCpuAllocation}
                    max={100}
                    step={5}
                  />
                  <p className="text-xs text-gray-500">Allocate CPU resources for this instance</p>
                </div>

                {/* Memory Allocation Slider */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Memory Allocation</Label>
                    <span className="text-sm font-medium">{memoryAllocation[0]} GB</span>
                  </div>
                  <Slider
                    value={memoryAllocation}
                    onValueChange={setMemoryAllocation}
                    max={32}
                    step={1}
                  />
                  <p className="text-xs text-gray-500">Allocate memory resources for this instance</p>
                </div>
              </div>
            </Card>

            {/* Estimated Cost Card */}
            <Card className="p-4 bg-blue-50 border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-blue-600" />
                <p className="text-sm font-medium">Estimated Cost Impact</p>
              </div>
              <div className="space-y-1 text-sm text-gray-700">
                <p>Current: $0.042/hr (~$30.24/month)</p>
                <p>After changes: {instanceType === 't3.medium' ? '$0.042/hr (~$30.24/month)' :
                  instanceType === 't3.large' ? '$0.083/hr (~$59.76/month)' :
                    instanceType === 't3.xlarge' ? '$0.166/hr (~$119.52/month)' :
                      instanceType === 't3.2xlarge' ? '$0.332/hr (~$239.04/month)' :
                        instanceType === 't3.small' ? '$0.021/hr (~$15.12/month)' : '$0.010/hr (~$7.20/month)'}</p>
              </div>
            </Card>
          </TabsContent>

          {/* Advanced Settings Tab */}
          <TabsContent value="settings" className="space-y-4 mt-4">
            {/* Storage Configuration */}
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <HardDrive className="h-5 w-5 text-green-600" />
                <h3 className="font-medium">Storage Configuration</h3>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="storage-size">Storage Size (GB)</Label>
                  <Input
                    id="storage-size"
                    type="number"
                    defaultValue="50"
                    max="1000"
                    min="8"
                  />
                  <p className="text-xs text-gray-500">Minimum: 8GB, Maximum: 1000GB</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="storage-type">Storage Type</Label>
                  <Select defaultValue="gp3">
                    <SelectTrigger id="storage-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gp2">General Purpose SSD (gp2)</SelectItem>
                      <SelectItem value="gp3">General Purpose SSD (gp3) - Recommended</SelectItem>
                      <SelectItem value="io1">Provisioned IOPS SSD (io1)</SelectItem>
                      <SelectItem value="io2">Provisioned IOPS SSD (io2)</SelectItem>
                      <SelectItem value="st1">Throughput Optimized HDD</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </Card>

            {/* Instance Behavior */}
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <SettingsIcon className="h-5 w-5 text-purple-600" />
                <h3 className="font-medium">Instance Behavior</h3>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto-restart on Failure</Label>
                    <p className="text-sm text-gray-600">Automatically restart instance if it fails</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Detailed Monitoring</Label>
                    <p className="text-sm text-gray-600">Enable CloudWatch detailed monitoring</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="backup-frequency">Backup Frequency</Label>
                  <Select defaultValue="daily">
                    <SelectTrigger id="backup-frequency">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hourly">Hourly</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="none">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="retention-days">Backup Retention (days)</Label>
                  <Input
                    id="retention-days"
                    type="number"
                    defaultValue="7"
                    min="1"
                    max="365"
                  />
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="flex gap-3 mt-6">
          <Button variant="outline" className="flex-1" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="flex-1 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
            onClick={handleSave}
          >
            Save Configuration
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
