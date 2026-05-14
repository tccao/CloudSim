// =============================================================================
// CreateInstanceModal.tsx
// =============================================================================
// Multi-step wizard modal for launching new EC2 instances. Guides users through
// selecting AMI, instance type, network/storage configuration, and review.
//
// API CALLS:
// - createInstance() -> POST /api/ec2/instances
//
// COMPONENT STRUCTURE:
// └── CreateInstanceModal
//     ├── Progress Indicator (Steps 1-4)
//     ├── Step 1: Name & AMI Selection
//     ├── Step 2: Instance Type Selection
//     ├── Step 3: Network & Storage Configuration
//     ├── Step 4: Review & Launch
//     └── Navigation Footer (Back/Next/Launch)
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useEffect, useState } from 'react';
import { createInstance } from '../api/instances';
import { getLaunchOptions, type AmiOption, type SecurityGroupOption, type SubnetOption, type VpcOption } from '../api/ec2';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Checkbox } from './ui/checkbox';


// =============================================================================
// TYPES
// =============================================================================

interface CreateInstanceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}


// =============================================================================
// CONSTANTS - Configuration Options
// =============================================================================

const fallbackAmiOptions: AmiOption[] = [
  { name: 'Amazon Linux 2023 AMI', id: 'ami-0c55b159cbfafe1f0', description: '64-bit (x86)', architecture: 'x86_64' },
  { name: 'Ubuntu Server 22.04 LTS', id: 'ami-0a2e8c7f3b8d4c5e6', description: '64-bit (x86)', architecture: 'x86_64' },
  { name: 'Windows Server 2022 Base', id: 'ami-0b1e2d3c4f5a6b7c8', description: '64-bit (x86)', architecture: 'x86_64' },
];

// Instance type options data
const instanceTypes = {
  't2.nano': { vcpu: 1, memory: 0.5, price: 0.0058 },
  't2.micro': { vcpu: 1, memory: 1, price: 0.0116 },
  't2.small': { vcpu: 1, memory: 2, price: 0.023 },
  't2.medium': { vcpu: 2, memory: 4, price: 0.046 },
  't2.large': { vcpu: 2, memory: 8, price: 0.092 },
};

const fallbackVpcOptions: VpcOption[] = [
  { id: 'vpc-0f966dca08a6c0d9b', name: 'cloudsim-vpc', is_default: false },
];

const fallbackSubnetOptions: SubnetOption[] = [
  { id: 'subnet-0204c01c4e5d0f86d', name: 'cloudsim-public', vpc_id: 'vpc-0f966dca08a6c0d9b', availability_zone: 'us-east-1a', default_for_az: false },
  { id: 'subnet-096492e1ec149a740', name: 'cloudsim-private', vpc_id: 'vpc-0f966dca08a6c0d9b', availability_zone: 'us-east-1a', default_for_az: false },
];

const fallbackSecurityGroupOptions: SecurityGroupOption[] = [
  { id: 'sg-0cd0cdc01b676a91e', name: 'cloudsim-ec2-sg', vpc_id: 'vpc-0f966dca08a6c0d9b', description: 'CloudSim EC2 security group' },
];


// =============================================================================
// COMPONENT
// =============================================================================

export function CreateInstanceModal({ open, onOpenChange }: CreateInstanceModalProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [step, setStep] = useState(1);
  const [isLaunching, setIsLaunching] = useState(false);
  const [amis, setAmis] = useState<AmiOption[]>(fallbackAmiOptions);
  const [vpcs, setVpcs] = useState<VpcOption[]>(fallbackVpcOptions);
  const [subnets, setSubnets] = useState<SubnetOption[]>(fallbackSubnetOptions);
  const [securityGroups, setSecurityGroups] = useState<SecurityGroupOption[]>(fallbackSecurityGroupOptions);

  // Form state
  const [instanceName, setInstanceName] = useState('web-server-01');
  const [selectedAmiId, setSelectedAmiId] = useState(fallbackAmiOptions[0].id);
  const [selectedInstanceType, setSelectedInstanceType] = useState('t2.nano');
  const [selectedVpcId, setSelectedVpcId] = useState(fallbackVpcOptions[0].id);
  const [selectedSubnetId, setSelectedSubnetId] = useState(fallbackSubnetOptions[0].id);
  const [selectedSecurityGroupId, setSelectedSecurityGroupId] = useState(fallbackSecurityGroupOptions[0].id);
  const [volumeSize, setVolumeSize] = useState('8');
  const [assignPublicIp, setAssignPublicIp] = useState(true);
  const [deleteOnTermination, setDeleteOnTermination] = useState(true);

  // ---------------------------------------------------------------------------
  // Computed Values
  // ---------------------------------------------------------------------------

  // Calculate estimated monthly cost
  const monthlyCost = (instanceTypes[selectedInstanceType as keyof typeof instanceTypes].price * 730).toFixed(2);
  const selectedAmi = amis.find((ami) => ami.id === selectedAmiId) || amis[0];
  const selectedVpc = vpcs.find((vpc) => vpc.id === selectedVpcId) || vpcs[0];
  const selectedSubnet = subnets.find((subnet) => subnet.id === selectedSubnetId) || subnets[0];
  const selectedSecurityGroup = securityGroups.find((sg) => sg.id === selectedSecurityGroupId) || securityGroups[0];

  useEffect(() => {
    if (!open) return;

    const loadLaunchOptions = async () => {
      try {
        const options = await getLaunchOptions();
        if (options.amis.length > 0) {
          setAmis(options.amis);
          setSelectedAmiId(options.defaults.ami_id || options.amis[0].id);
        }
        if (options.vpcs.length > 0) {
          setVpcs(options.vpcs);
          setSelectedVpcId(options.defaults.vpc_id || options.vpcs[0].id);
        }
        if (options.subnets.length > 0) {
          setSubnets(options.subnets);
          setSelectedSubnetId(options.defaults.subnet_id || options.subnets[0].id);
        }
        if (options.security_groups.length > 0) {
          setSecurityGroups(options.security_groups);
          setSelectedSecurityGroupId(options.defaults.security_group_id || options.security_groups[0].id);
        }
        if (options.instance_types.includes(options.defaults.instance_type)) {
          setSelectedInstanceType(options.defaults.instance_type);
        }
        setVolumeSize(String(options.defaults.volume_size || 8));
        setAssignPublicIp(options.defaults.assign_public_ip);
        setDeleteOnTermination(options.defaults.delete_on_termination);
      } catch (error) {
        console.error('Failed to load launch options:', error);
      }
    };

    loadLaunchOptions();
  }, [open]);

  useEffect(() => {
    const matchingSubnets = subnets.filter((subnet) => subnet.vpc_id === selectedVpcId);
    if (matchingSubnets.length > 0 && !matchingSubnets.some((subnet) => subnet.id === selectedSubnetId)) {
      setSelectedSubnetId(matchingSubnets[0].id);
    }

    const matchingSecurityGroups = securityGroups.filter((sg) => !sg.vpc_id || sg.vpc_id === selectedVpcId);
    if (
      matchingSecurityGroups.length > 0 &&
      !matchingSecurityGroups.some((sg) => sg.id === selectedSecurityGroupId)
    ) {
      setSelectedSecurityGroupId(matchingSecurityGroups[0].id);
    }
  }, [securityGroups, selectedSecurityGroupId, selectedSubnetId, selectedVpcId, subnets]);

  // ---------------------------------------------------------------------------
  // Navigation Handlers
  // ---------------------------------------------------------------------------

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  // ---------------------------------------------------------------------------
  // API Handler - Launch Instance
  // ---------------------------------------------------------------------------

  const handleLaunch = async () => {
    try {
      setIsLaunching(true);

      // API CALL: POST /api/ec2/instances
      await createInstance({
        name: instanceName,
        instance_type: selectedInstanceType,
        image_id: selectedAmiId,
        subnet_id: selectedSubnetId,
        security_group_ids: selectedSecurityGroupId ? [selectedSecurityGroupId] : undefined,
        volume_size: Number(volumeSize),
        volume_type: 'gp3',
        assign_public_ip: assignPublicIp,
        delete_on_termination: deleteOnTermination,
      });

      toast.success('Instance launched successfully');
      onOpenChange(false);
      setStep(1);
    } catch (error) {
      console.error('Failed to launch instance:', error);
      toast.error('Failed to launch instance');
    } finally {
      setIsLaunching(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Launch EC2 Instance</DialogTitle>
          <DialogDescription>
            Configure your instance settings - Step {step} of 4
          </DialogDescription>
        </DialogHeader>

        {/* Progress indicator */}
        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`flex-1 h-1 rounded ${s <= step ? 'bg-blue-600' : 'bg-gray-200'
                }`}
            />
          ))}
        </div>

        {/* Step 1: Name and AMI */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="instance-name">Instance Name</Label>
              <Input
                id="instance-name"
                placeholder="my-web-server"
                value={instanceName}
                onChange={(e) => setInstanceName(e.target.value)}
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <Label>Amazon Machine Image (AMI)</Label>
              <RadioGroup value={selectedAmiId} onValueChange={setSelectedAmiId}>
                {amis.map((ami) => (
                  <Card className="p-4 mb-3" key={ami.id}>
                    <div className="flex items-start gap-3">
                      <RadioGroupItem value={ami.id} id={ami.id} className="mt-1" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <label htmlFor={ami.id} className="cursor-pointer">
                            {ami.name}
                          </label>
                          <Badge variant="secondary">{ami.architecture}</Badge>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          {ami.id} • {ami.description || 'AWS managed image'}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </RadioGroup>
            </div>
          </div>
        )}

        {/* Step 2: Instance Type */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="space-y-3">
              <Label>Instance Type</Label>
              <RadioGroup value={selectedInstanceType} onValueChange={setSelectedInstanceType}>
                <Card className="p-4 mb-3">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="t2.nano" id="t2.nano" className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <label htmlFor="t2.nano" className="cursor-pointer">
                          t2.nano
                        </label>
                        <Badge variant="secondary">Free tier eligible</Badge>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        1 vCPU • 512 MiB Memory
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">$0.0058/hour</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4 mb-3">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="t2.small" id="t2.small" className="mt-1" />
                    <div className="flex-1">
                      <label htmlFor="t2.small" className="cursor-pointer">
                        t2.small
                      </label>
                      <p className="text-sm text-gray-500 mt-1">
                        1 vCPU • 2 GiB Memory
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">$0.023/hour</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4 mb-3">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="t2.medium" id="t2.medium" className="mt-1" />
                    <div className="flex-1">
                      <label htmlFor="t2.medium" className="cursor-pointer">
                        t2.medium
                      </label>
                      <p className="text-sm text-gray-500 mt-1">
                        2 vCPU • 4 GiB Memory
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">$0.046/hour</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="t2.large" id="t2.large" className="mt-1" />
                    <div className="flex-1">
                      <label htmlFor="t2.large" className="cursor-pointer">
                        t2.large
                      </label>
                      <p className="text-sm text-gray-500 mt-1">
                        2 vCPU • 8 GiB Memory
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">$0.092/hour</p>
                    </div>
                  </div>
                </Card>
              </RadioGroup>
            </div>
          </div>
        )}

        {/* Step 3: Network & Storage */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="font-medium">Network Settings</h3>

              <div className="space-y-2">
                <Label htmlFor="vpc">VPC</Label>
                <Select value={selectedVpcId} onValueChange={setSelectedVpcId}>
                  <SelectTrigger id="vpc">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {vpcs.map((vpc) => (
                      <SelectItem key={vpc.id} value={vpc.id}>
                        {vpc.id} ({vpc.name})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="subnet">Subnet</Label>
                <Select value={selectedSubnetId} onValueChange={setSelectedSubnetId}>
                  <SelectTrigger id="subnet">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {subnets
                      .filter((subnet) => !selectedVpcId || subnet.vpc_id === selectedVpcId)
                      .map((subnet) => (
                        <SelectItem key={subnet.id} value={subnet.id}>
                          {subnet.name} ({subnet.availability_zone || subnet.id})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="security-group">Security Group</Label>
                <Select value={selectedSecurityGroupId} onValueChange={setSelectedSecurityGroupId}>
                  <SelectTrigger id="security-group">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {securityGroups
                      .filter((sg) => !selectedVpcId || !sg.vpc_id || sg.vpc_id === selectedVpcId)
                      .map((sg) => (
                        <SelectItem key={sg.id} value={sg.id}>
                          {sg.id} ({sg.name})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  id="auto-assign-ip"
                  checked={assignPublicIp}
                  onCheckedChange={(checked) => setAssignPublicIp(checked === true)}
                />
                <label
                  htmlFor="auto-assign-ip"
                  className="text-sm cursor-pointer"
                >
                  Auto-assign public IP
                </label>
              </div>
            </div>

            <Separator />

            <div className="space-y-3">
              <h3 className="font-medium">Storage Configuration</h3>

              <Card className="p-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Root Volume (EBS)</span>
                    <Badge variant="outline">gp3</Badge>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="volume-size">Size (GiB)</Label>
                  <Input
                    id="volume-size"
                    type="number"
                    value={volumeSize}
                    onChange={(e) => setVolumeSize(e.target.value)}
                      min="8"
                      max="1000"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="delete-on-termination"
                      checked={deleteOnTermination}
                      onCheckedChange={(checked) => setDeleteOnTermination(checked === true)}
                    />
                    <label
                      htmlFor="delete-on-termination"
                      className="text-sm cursor-pointer"
                    >
                      Delete on termination
                    </label>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="space-y-4">
            <h3 className="font-medium">Review and Launch</h3>

            <Card className="p-4">
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Instance Name</span>
                  <span className="text-sm">{instanceName}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">AMI</span>
                  <span className="text-sm">{selectedAmi?.name}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Instance Type</span>
                  <span className="text-sm">{selectedInstanceType}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">VPC</span>
                  <span className="text-sm">{selectedVpc ? `${selectedVpc.id} (${selectedVpc.name})` : '-'}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Subnet</span>
                  <span className="text-sm">
                    {selectedSubnet ? `${selectedSubnet.name} (${selectedSubnet.availability_zone || selectedSubnet.id})` : '-'}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Security Group</span>
                  <span className="text-sm">
                    {selectedSecurityGroup ? `${selectedSecurityGroup.id} (${selectedSecurityGroup.name})` : '-'}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Storage</span>
                  <span className="text-sm">{volumeSize} GiB (gp3)</span>
                </div>
              </div>
            </Card>

            <Card className="p-4 bg-blue-50 border-blue-200">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm">Estimated monthly cost</p>
                  <p className="text-sm text-gray-600">Based on 730 hours/month</p>
                </div>
                <p className="text-2xl">${monthlyCost}/mo</p>
              </div>
            </Card>
          </div>
        )}

        {/* Footer Navigation */}
        <DialogFooter>
          <div className="flex justify-between w-full">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={step === 1}
            >
              Back
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              {step < 4 ? (
                <Button onClick={handleNext}>Next</Button>
              ) : (
                <Button onClick={handleLaunch} disabled={isLaunching}>
                  {isLaunching && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isLaunching ? 'Launching...' : 'Launch Instance'}
                </Button>
              )}
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
