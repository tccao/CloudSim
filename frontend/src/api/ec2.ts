/**
 * =============================================================================
 * CloudSim EC2 API Client
 * =============================================================================
 * 
 * PURPOSE:
 * This file provides TypeScript functions that call the CloudSim backend API.
 * These are HTTP wrappers - they do NOT call AWS directly.
 * 
 * ARCHITECTURE:
 *   Browser (this file)  →  Backend (FastAPI)  →  AWS (boto3)
 *   listInstances()      →  GET /api/ec2/...   →  ec2.describe_instances()
 * 
 * WHY THIS LAYER EXISTS:
 *   1. Security: AWS credentials stay on backend, never exposed to browser
 *   2. Types: TypeScript interfaces for all API responses
 *   3. Reusability: Import functions instead of duplicating axios calls
 * 
 * =============================================================================
 */

import { api } from './client';


// =============================================================================
// SECTION 1: TYPE DEFINITIONS
// =============================================================================
// These interfaces define the shape of data returned by the backend API.
// They help TypeScript catch errors at compile time.

/** Basic instance info returned by list endpoint */
export interface EC2Instance {
    instance_id: string;
    name: string;
    instance_type: string;
    state: string;
    public_ip: string | null;
    private_ip: string | null;
    launch_time: string | null;
    availability_zone: string;
}

/** Full instance details including security groups, storage, tags */
export interface EC2InstanceDetails extends EC2Instance {
    key_name: string | null;
    platform: string;
    tenancy: string;
    ami_id: string;
    monitoring: string;
    public_dns: string | null;
    private_dns: string | null;
    vpc_id: string | null;
    subnet_id: string | null;
    security_groups: SecurityGroup[];
    block_devices: BlockDevice[];
    tags: Tag[];
    iam_role: string | null;
}

export interface SecurityGroup {
    GroupId: string;
    GroupName: string;
}

export interface BlockDevice {
    device_name: string;
    volume_id: string;
    size: number;
    volume_type: string;
    iops?: number;
    throughput?: number;
    encrypted: boolean;
    delete_on_termination: boolean;
}

export interface Tag {
    Key: string;
    Value: string;
}

export interface CreateInstanceRequest {
    name: string;
    instance_type: string;
}

export interface ActionResponse {
    message: string;
    instance_id: string;
}


// =============================================================================
// SECTION 2: INSTANCE CRUD OPERATIONS
// =============================================================================

/**
 * List all EC2 instances.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/ec2/instances \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 * 
 * RESPONSE EXAMPLE:
 * ```json
 * [
 *   {
 *     "instance_id": "i-0abc123def456",
 *     "name": "web-server-01",
 *     "instance_type": "t2.micro",
 *     "state": "running",
 *     "public_ip": "54.123.45.67",
 *     "private_ip": "172.31.16.22"
 *   }
 * ]
 * ```
 */
export async function listInstances(): Promise<EC2Instance[]> {
    const response = await api.get<EC2Instance[]>('/api/ec2/instances');
    return response.data;
}


/**
 * Get detailed information for a specific instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/ec2/instances/i-0abc123def456 \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function getInstance(instanceId: string): Promise<EC2InstanceDetails> {
    const response = await api.get<EC2InstanceDetails>(`/api/ec2/instances/${instanceId}`);
    return response.data;
}


/**
 * Create a new EC2 instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X POST http://localhost:8000/api/ec2/instances \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN" \
 *   -H "Content-Type: application/json" \
 *   -d '{"name": "test-server", "instance_type": "t2.micro"}'
 * ```
 * 
 * REQUIRED ROLE: DevOps Engineer or Admin
 */
export async function createInstance(data: CreateInstanceRequest): Promise<ActionResponse> {
    const response = await api.post<ActionResponse>('/api/ec2/instances', data);
    return response.data;
}


/**
 * Terminate (delete) an EC2 instance permanently.
 * 
 * CURL TEST:
 * ```bash
 * curl -X DELETE http://localhost:8000/api/ec2/instances/i-0abc123def456 \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 * 
 * REQUIRED ROLE: Admin only
 * WARNING: This action is irreversible!
 */
export async function terminateInstance(instanceId: string): Promise<ActionResponse> {
    const response = await api.delete<ActionResponse>(`/api/ec2/instances/${instanceId}`);
    return response.data;
}


// =============================================================================
// SECTION 3: INSTANCE LIFECYCLE ACTIONS
// =============================================================================

/**
 * Start a stopped EC2 instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X POST http://localhost:8000/api/ec2/instances/i-0abc123def456/start \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function startInstance(instanceId: string): Promise<ActionResponse> {
    const response = await api.post<ActionResponse>(`/api/ec2/instances/${instanceId}/start`);
    return response.data;
}


/**
 * Stop a running EC2 instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X POST http://localhost:8000/api/ec2/instances/i-0abc123def456/stop \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function stopInstance(instanceId: string): Promise<ActionResponse> {
    const response = await api.post<ActionResponse>(`/api/ec2/instances/${instanceId}/stop`);
    return response.data;
}


/**
 * Reboot an EC2 instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X POST http://localhost:8000/api/ec2/instances/i-0abc123def456/reboot \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function rebootInstance(instanceId: string): Promise<ActionResponse> {
    const response = await api.post<ActionResponse>(`/api/ec2/instances/${instanceId}/reboot`);
    return response.data;
}


/**
 * Get available instance types for creating new instances.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/ec2/instance-types \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function getInstanceTypes(): Promise<string[]> {
    const response = await api.get<{ instance_types: string[] }>('/api/ec2/instance-types');
    return response.data.instance_types;
}


// =============================================================================
// SECTION 4: CLOUDWATCH METRICS
// =============================================================================

export interface MetricDataPoint {
    timestamp: string;
    value: number;
}

export interface InstanceMetrics {
    instance_id: string;
    cpu_utilization: MetricDataPoint[];
    network_in: MetricDataPoint[];
    network_out: MetricDataPoint[];
    disk_read_ops: MetricDataPoint[];
    disk_write_ops: MetricDataPoint[];
}

export interface CurrentMetrics {
    instance_id: string;
    cpu_percent: number;
    network_in_bytes: number;
    network_out_bytes: number;
}


/**
 * Get CloudWatch metrics history for an instance.
 * 
 * CURL TEST:
 * ```bash
 * # Get last 60 minutes of metrics
 * curl -X GET "http://localhost:8000/api/ec2/instances/i-0abc123def456/metrics?period=60" \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 * 
 * @param instanceId - EC2 instance ID
 * @param periodMinutes - How far back to fetch (default: 60)
 */
export async function getInstanceMetrics(
    instanceId: string,
    periodMinutes: number = 60
): Promise<InstanceMetrics> {
    const response = await api.get<InstanceMetrics>(
        `/api/ec2/instances/${instanceId}/metrics?period=${periodMinutes}`
    );
    return response.data;
}


/**
 * Get current (latest) metrics for an instance.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/ec2/instances/i-0abc123def456/metrics/current \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function getCurrentMetrics(instanceId: string): Promise<CurrentMetrics> {
    const response = await api.get<CurrentMetrics>(
        `/api/ec2/instances/${instanceId}/metrics/current`
    );
    return response.data;
}


// =============================================================================
// SECTION 5: COST EXPLORER
// =============================================================================

export interface DailyCost {
    date: string;
    compute: number;
    storage: number;
    network: number;
    total: number;
}

export interface CostSummary {
    month_to_date: number;
    projected_monthly: number;
    days_elapsed: number;
}


/**
 * Get daily cost breakdown for the last N days.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET "http://localhost:8000/api/ec2/costs/daily?days=7" \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function getDailyCosts(days: number = 7): Promise<DailyCost[]> {
    const response = await api.get<DailyCost[]>(`/api/ec2/costs/daily?days=${days}`);
    return response.data;
}


/**
 * Get current month cost summary.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/ec2/costs/summary \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 */
export async function getCostSummary(): Promise<CostSummary> {
    const response = await api.get<CostSummary>('/api/ec2/costs/summary');
    return response.data;
}


// =============================================================================
// QUICK REFERENCE: HOW TO GET A JWT TOKEN FOR TESTING
// =============================================================================
/*
 * Before testing with curl, you need a JWT token. Get one with:
 * 
 * ```bash
 * # Login to get a token (OAuth2 requires form-urlencoded, NOT JSON!)
 * curl -X POST http://localhost:8000/api/auth/login \
 *   -H "Content-Type: application/x-www-form-urlencoded" \
 *   -d "username=admin@gmail.com&password=admin123"
 * 
 * # Response:
 * # {"access_token": "eyJhbGci...", "token_type": "bearer"}
 * 
 * # Use the token in subsequent requests:
 * export TOKEN="eyJhbGci..."
 * curl -X GET http://localhost:8000/api/ec2/instances \
 *   -H "Authorization: Bearer $TOKEN"
 * ```
 * 
 * TEST ACCOUNTS:
 *   admin@gmail.com / admin123 (Admin)
 *   dev@gmail.com / dev123 (Developer)
 *   deng@gmail.com / deng123 (DevOps Engineer)
 *   user@gmail.com / user123 (User)
 */

