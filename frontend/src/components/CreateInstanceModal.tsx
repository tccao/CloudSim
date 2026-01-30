import { useState } from 'react';
import { createInstance } from '../api/instances';
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

interface CreateInstanceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// AMI options data
const amiOptions = {
  'ami-1': { name: 'Amazon Linux 2023 AMI', id: 'ami-0c55b159cbfafe1f0' },
  'ami-2': { name: 'Ubuntu Server 22.04 LTS', id: 'ami-0a2e8c7f3b8d4c5e6' },
  'ami-3': { name: 'Windows Server 2022 Base', id: 'ami-0b1e2d3c4f5a6b7c8' },
};

// Instance type options data
const instanceTypes = {
  't2.nano': { vcpu: 1, memory: 0.5, price: 0.0058 },
  't2.micro': { vcpu: 1, memory: 1, price: 0.0116 },
  't2.small': { vcpu: 1, memory: 2, price: 0.023 },
  't2.medium': { vcpu: 2, memory: 4, price: 0.046 },
  't2.large': { vcpu: 2, memory: 8, price: 0.092 },
};

// VPC options data
const vpcOptions = {
  'cloudsim-vpc': 'vpc-0f966dca08a6c0d9b (cloudsim-vpc)',
};

// Subnet options data
const subnetOptions = {
  'cloudsim-public': 'cloudsim-public-0204c01c4e5d0f86d (us-east-1a)',
  'cloudsim-private': 'cloudsim-private-096492e1ec149a740 (us-east-1a)',
};

// Security group options data
const sgOptions = {
  'cloudsim-ec2-sg': 'sg-0cd0cdc01b676a91e (cloudsim-ec2-sg)',
};

export function CreateInstanceModal({ open, onOpenChange }: CreateInstanceModalProps) {
  const [step, setStep] = useState(1);
  const [isLaunching, setIsLaunching] = useState(false);

  // Form state
  const [instanceName, setInstanceName] = useState('web-server-01');
  const [selectedAmi, setSelectedAmi] = useState('ami-1');
  const [selectedInstanceType, setSelectedInstanceType] = useState('t2.nano');
  const [selectedVpc, setSelectedVpc] = useState('cloudsim-vpc');
  const [selectedSubnet, setSelectedSubnet] = useState('cloudsim-public');
  const [selectedSecurityGroup, setSelectedSecurityGroup] = useState('cloudsim-ec2-sg');
  const [volumeSize, setVolumeSize] = useState('1');

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  // Calculate estimated monthly cost
  const monthlyCost = (instanceTypes[selectedInstanceType as keyof typeof instanceTypes].price * 730).toFixed(2);

  const handleLaunch = async () => {
    try {
      setIsLaunching(true);

      await createInstance({
        name: instanceName,
        instance_type: selectedInstanceType,
      });

      toast.success('Instance launched successfully');
      onOpenChange(false);
      setStep(1);
      // Trigger a refresh somehow? 
      // ideally we should pass a callback prop `onSuccess` or use a context.
      // For now, let's just close. The user might need to manually refresh dashboard 
      // unless we fix DashboardPage to auto-refresh or share state.
      // Let's add a hack: reload window? No, bad UX.
      // Better: Add onSuccess prop.
    } catch (error) {
      console.error('Failed to launch instance:', error);
      toast.error('Failed to launch instance');
    } finally {
      setIsLaunching(false);
    }
  };


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
              <RadioGroup value={selectedAmi} onValueChange={setSelectedAmi}>
                <Card className="p-4 mb-3">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="ami-1" id="ami-1" className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <label htmlFor="ami-1" className="cursor-pointer">
                          Amazon Linux 2023 AMI
                        </label>
                        <Badge variant="secondary">Free tier eligible</Badge>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        ami-0c55b159cbfafe1f0 • 64-bit (x86)
                      </p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4 mb-3">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="ami-2" id="ami-2" className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <label htmlFor="ami-2" className="cursor-pointer">
                          Ubuntu Server 22.04 LTS
                        </label>
                        <Badge variant="secondary">Free tier eligible</Badge>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        ami-0a2e8c7f3b8d4c5e6 • 64-bit (x86)
                      </p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-start gap-3">
                    <RadioGroupItem value="ami-3" id="ami-3" className="mt-1" />
                    <div className="flex-1">
                      <label htmlFor="ami-3" className="cursor-pointer">
                        Windows Server 2022 Base
                      </label>
                      <p className="text-sm text-gray-500 mt-1">
                        ami-0b1e2d3c4f5a6b7c8 • 64-bit (x86)
                      </p>
                    </div>
                  </div>
                </Card>
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
                <Select value={selectedVpc} onValueChange={setSelectedVpc}>
                  <SelectTrigger id="vpc">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cloudsim-vpc">vpc-0f966dca08a6c0d9b (cloudsim-vpc)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="subnet">Subnet</Label>
                <Select value={selectedSubnet} onValueChange={setSelectedSubnet}>
                  <SelectTrigger id="subnet">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cloudsim-public">cloudsim-public-0204c01c4e5d0f86d (us-east-1a)</SelectItem>
                    <SelectItem value="cloudsim-private">cloudsim-private-096492e1ec149a740 (us-east-1a)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="security-group">Security Group</Label>
                <Select value={selectedSecurityGroup} onValueChange={setSelectedSecurityGroup}>
                  <SelectTrigger id="security-group">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cloudsim-ec2-sg">sg-0cd0cdc01b676a91e (cloudsim-ec2-sg)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox id="auto-assign-ip" defaultChecked />
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
                    <Checkbox id="delete-on-termination" defaultChecked />
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
                  <span className="text-sm">{amiOptions[selectedAmi as keyof typeof amiOptions].name}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Instance Type</span>
                  <span className="text-sm">{selectedInstanceType}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">VPC</span>
                  <span className="text-sm">{vpcOptions[selectedVpc as keyof typeof vpcOptions]}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Subnet</span>
                  <span className="text-sm">{subnetOptions[selectedSubnet as keyof typeof subnetOptions]}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Security Group</span>
                  <span className="text-sm">{sgOptions[selectedSecurityGroup as keyof typeof sgOptions]}</span>
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
