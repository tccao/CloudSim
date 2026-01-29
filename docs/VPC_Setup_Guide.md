# CloudSim VPC Setup Guide

Complete guide to set up a dedicated VPC for CloudSim-managed EC2 instances.

---

## Overview

This guide creates a dedicated network environment for CloudSim:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CloudSim VPC (10.0.0.0/16)                        │
│                                                                          │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐       │
│  │   Public Subnet             │  │   Private Subnet            │       │
│  │   10.0.1.0/24              │  │   10.0.2.0/24              │       │
│  │                             │  │                             │       │
│  │   ┌─────────────────┐       │  │   (Future: internal         │       │
│  │   │ EC2 Instance    │       │  │    services)                │       │
│  │   │ (web-facing)    │       │  │                             │       │
│  │   └────────┬────────┘       │  │                             │       │
│  └────────────┼────────────────┘  └─────────────────────────────┘       │
│               │                                                          │
│  ┌────────────┴────────────────┐                                        │
│  │     Internet Gateway        │                                        │
│  └────────────┬────────────────┘                                        │
└───────────────┼─────────────────────────────────────────────────────────┘
                │
         ┌──────┴──────┐
         │  Internet   │
         └─────────────┘
```

---

## Part 1: Create the VPC

### Step 1.1: Create VPC

1. Go to: https://console.aws.amazon.com/vpc/home#CreateVpc
2. Select: **VPC only**
3. Configure:
   - Name tag: `cloudsim-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - IPv6 CIDR: No IPv6 CIDR block
   - Tenancy: Default
4. Click **Create VPC**
5. **Save the VPC ID** (e.g., `vpc-0abc123...`)

---

## Part 2: Create Subnets

### Step 2.1: Create Public Subnet

1. Go to: https://console.aws.amazon.com/vpc/home#CreateSubnet
2. Select VPC: `cloudsim-vpc`
3. Configure:
   - Subnet name: `cloudsim-public`
   - Availability Zone: `us-east-1a` (or your preferred AZ)
   - IPv4 CIDR: `10.0.1.0/24`
4. Click **Create subnet**
5. **Save the Subnet ID** (e.g., `subnet-0abc123...`)

### Step 2.2: Enable Auto-assign Public IP

1. Select the `cloudsim-public` subnet
2. Click **Actions** → **Edit subnet settings**
3. Check: **Enable auto-assign public IPv4 address**
4. Click **Save**

### Step 2.3: Create Private Subnet (Optional)

1. Go to: https://console.aws.amazon.com/vpc/home#CreateSubnet
2. Select VPC: `cloudsim-vpc`
3. Configure:
   - Subnet name: `cloudsim-private`
   - Availability Zone: `us-east-1a`
   - IPv4 CIDR: `10.0.2.0/24`
4. Click **Create subnet**

---

## Part 3: Create Internet Gateway

### Step 3.1: Create Gateway

1. Go to: https://console.aws.amazon.com/vpc/home#CreateInternetGateway
2. Name tag: `cloudsim-igw`
3. Click **Create internet gateway**

### Step 3.2: Attach to VPC

1. Select `cloudsim-igw`
2. Click **Actions** → **Attach to VPC**
3. Select: `cloudsim-vpc`
4. Click **Attach internet gateway**

---

## Part 4: Configure Route Table

### Step 4.1: Find or Create Route Table

1. Go to: https://console.aws.amazon.com/vpc/home#RouteTables
2. Find the route table for `cloudsim-vpc` (created automatically with VPC)
3. Rename it to: `cloudsim-public-rt`

### Step 4.2: Add Internet Route

1. Select `cloudsim-public-rt`
2. Click **Routes** tab → **Edit routes**
3. Add route:
   - Destination: `0.0.0.0/0`
   - Target: Select `cloudsim-igw`
4. Click **Save changes**

### Step 4.3: Associate with Public Subnet

1. Click **Subnet associations** tab → **Edit subnet associations**
2. Select: `cloudsim-public`
3. Click **Save associations**

---

## Part 5: Create Security Group

### Step 5.1: Create Security Group

1. Go to: https://console.aws.amazon.com/ec2/home#CreateSecurityGroup
2. Configure:
   - Security group name: `cloudsim-ec2-sg`
   - Description: `Security group for CloudSim managed instances`
   - VPC: `cloudsim-vpc`

### Step 5.2: Add Inbound Rules

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | Your IP / `0.0.0.0/0` | SSH access |
| HTTP | TCP | 80 | `0.0.0.0/0` | Web traffic |
| HTTPS | TCP | 443 | `0.0.0.0/0` | Secure web traffic |

> **Security Note:** For production, restrict SSH to specific IPs instead of `0.0.0.0/0`

### Step 5.3: Outbound Rules

Keep default: Allow all outbound traffic (`0.0.0.0/0`)

3. Click **Create security group**
4. **Save the Security Group ID** (e.g., `sg-0abc123...`)

---

## Part 6: Configure CloudSim

### Step 6.1: Update .env

Add your VPC resources to the backend `.env` file:

```bash
# VPC Configuration
CLOUDSIM_VPC_ID=vpc-0abc123...       # Your VPC ID
CLOUDSIM_SUBNET_ID=subnet-0abc123... # Your public subnet ID
CLOUDSIM_SECURITY_GROUP_ID=sg-0abc123... # Your security group ID
```

### Step 6.2: Restart Backend

```bash
cd /home/tinhc/CloudSim/backend
# Restart the server to pick up new config
uvicorn app.main:app --reload
```

---

## Part 7: Verification

### Test Instance Creation

1. Create a new instance through CloudSim UI
2. Verify in AWS Console:
   - Instance is in `cloudsim-vpc`
   - Instance is in `cloudsim-public` subnet
   - Security group `cloudsim-ec2-sg` is attached

### Test Network Connectivity

```bash
# Get the instance public IP from CloudSim
# SSH into the instance (if you have a key pair)
ssh ec2-user@<public-ip>

# Or test HTTP if you install a web server
curl http://<public-ip>
```

---

## Summary: Resource IDs

After completing setup, you should have:

| Resource | Name | ID |
|----------|------|-----|
| VPC | `cloudsim-vpc` | `vpc-...` |
| Public Subnet | `cloudsim-public` | `subnet-...` |
| Private Subnet | `cloudsim-private` | `subnet-...` |
| Internet Gateway | `cloudsim-igw` | `igw-...` |
| Route Table | `cloudsim-public-rt` | `rtb-...` |
| Security Group | `cloudsim-ec2-sg` | `sg-...` |

---

## Cleanup (If Needed)

To delete VPC resources, delete in this order:
1. Terminate all EC2 instances in the VPC
2. Delete Security Groups (except default)
3. Delete Subnets
4. Detach and delete Internet Gateway
5. Delete Route Tables (except main)
6. Delete VPC

---

*Reference: CloudSim Architecture Manual*
