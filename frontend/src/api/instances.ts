/**
 * Instances API - Now uses real AWS EC2 via backend
 */
import * as ec2Api from './ec2';

export interface Instance {
    id: string;
    name: string;
    type: string;
    state: 'running' | 'stopped' | 'terminated' | 'creating' | 'pending' | 'shutting-down';
    cpu: number;
    memory: number;
    created_at?: string;
    zone?: string;
    publicIp?: string;
    privateIp?: string;
    uptime?: string;
}

export interface InstanceCreate {
    name: string;
    instance_type: string;
}

// Map instance type to CPU/Memory specs
const instanceSpecs: Record<string, { cpu: number; memory: number }> = {
    't2.nano': { cpu: 1, memory: 0.5 },
    't2.micro': { cpu: 1, memory: 1 },
    't2.small': { cpu: 1, memory: 2 },
    't2.medium': { cpu: 2, memory: 4 },
    't2.large': { cpu: 2, memory: 8 },
};

// Calculate uptime from launch time
const calculateUptime = (launchTime: string | null): string => {
    if (!launchTime) return '-';
    const launched = new Date(launchTime);
    const now = new Date();
    const diffMs = now.getTime() - launched.getTime();
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    return `${days}d ${hours}h`;
};

// Map EC2 instance to dashboard Instance type
const mapEC2ToInstance = (ec2: ec2Api.EC2Instance): Instance => {
    const specs = instanceSpecs[ec2.instance_type] || { cpu: 1, memory: 1 };
    return {
        id: ec2.instance_id,
        name: ec2.name || ec2.instance_id,
        type: ec2.instance_type,
        state: ec2.state as Instance['state'],
        cpu: specs.cpu,
        memory: specs.memory,
        created_at: ec2.launch_time || undefined,
        zone: ec2.availability_zone,
        publicIp: ec2.public_ip || '-',
        privateIp: ec2.private_ip || '-',
        uptime: calculateUptime(ec2.launch_time),
    };
};

export const fetchInstances = async (): Promise<Instance[]> => {
    const ec2Instances = await ec2Api.listInstances();
    return ec2Instances.map(mapEC2ToInstance);
};

export const createInstance = async (data: InstanceCreate): Promise<Instance> => {
    const result = await ec2Api.createInstance({
        name: data.name,
        instance_type: data.instance_type,
    });

    // Get specs for the instance type
    const specs = instanceSpecs[data.instance_type] || { cpu: 1, memory: 1 };

    // Return a pending instance (will be fetched on next refresh)
    return {
        id: result.instance_id,
        name: data.name,
        type: data.instance_type,
        state: 'pending',
        cpu: specs.cpu,
        memory: specs.memory,
        zone: 'us-east-1a',
        publicIp: '-',
        privateIp: '-',
        uptime: '-',
    };
};

export const deleteInstance = async (id: string): Promise<void> => {
    await ec2Api.terminateInstance(id);
};

export const getInstance = async (id: string): Promise<Instance> => {
    const ec2Instance = await ec2Api.getInstance(id);
    return mapEC2ToInstance(ec2Instance);
};

export const startInstance = async (id: string): Promise<void> => {
    await ec2Api.startInstance(id);
};

export const stopInstance = async (id: string): Promise<void> => {
    await ec2Api.stopInstance(id);
};

export const rebootInstance = async (id: string): Promise<void> => {
    await ec2Api.rebootInstance(id);
};
