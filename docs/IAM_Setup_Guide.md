# CloudSim AWS IAM Setup Guide

---

## Overview

We will create:
1. **One IAM User** (`cloudsim-service`) - Used by the backend application
2. **Three IAM Roles** - One for each CloudSim user role, assumed via STS

```
Database Users              IAM Roles
─────────────────────       ──────────────────────────
admin@gmail.com (Admin)     → CloudSimAdminRole (full access)
devops@gmail.com (DevOps)   → CloudSimDevOpsRole (full EC2, no terminate)
user@gmail.com (User)       → CloudSimUserRole (view + start/stop only)
```

---

## Part 1: Clean Up Old IAM Resources

### Step 1.1: Delete Old IAM User (AWS Console)

1. Go to: https://console.aws.amazon.com/iam/home#/users
2. Find `cloudsim` user
3. Click on the user name
4. Go to **Security credentials** tab
5. Delete any **Access keys**
6. Go back to Users list
7. Select the user checkbox
8. Click **Delete**
9. Type the user name to confirm

### Step 1.2: Delete Old IAM Roles (if any)

1. Go to: https://console.aws.amazon.com/iam/home#/roles
2. Search for `CloudSim`
3. Delete any existing CloudSim roles

---

## Part 2: Create IAM Policies

### Step 2.1: Create Admin Policy

1. Go to: https://console.aws.amazon.com/iam/home#/policies
2. Click **Create policy**
3. Select **JSON** tab
4. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "FullEC2Access",
            "Effect": "Allow",
            "Action": "ec2:*",
            "Resource": "*"
        },
        {
            "Sid": "FullCloudWatchAccess",
            "Effect": "Allow",
            "Action": "cloudwatch:*",
            "Resource": "*"
        },
        {
            "Sid": "CostExplorerAccess",
            "Effect": "Allow",
            "Action": "ce:*",
            "Resource": "*"
        }
    ]
}
```

5. Click **Next**
6. Name: `CloudSimAdminPolicy`
7. Description: `Full EC2, CloudWatch, and Cost Explorer access for CloudSim admins`
8. Click **Create policy**

---

### Step 2.2: Create DevOps Engineer Policy

**DevOps = Developer + create instances**

1. Click **Create policy**
2. Select **JSON** tab
3. Paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2ReadAndCreate",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:DescribeImages",
                "ec2:DescribeVolumes",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeKeyPairs",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:RebootInstances",
                "ec2:RunInstances",
                "ec2:CreateTags"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchMetrics",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "cloudwatch:GetMetricData"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CostExplorerRead",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyTerminate",
            "Effect": "Deny",
            "Action": "ec2:TerminateInstances",
            "Resource": "*"
        },
        {
            "Sid": "DenyVPCChanges",
            "Effect": "Deny",
            "Action": [
                "ec2:CreateVpc",
                "ec2:DeleteVpc",
                "ec2:ModifyVpc*"
            ],
            "Resource": "*"
        }
    ]
}
```

4. Name: `CloudSimDevOpsPolicy`
5. Create policy

---

### Step 2.3: Create User (Basic) Policy

**User = View instances, start/stop own instances, view costs**

1. Click **Create policy**
2. Select **JSON** tab
3. Paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2ReadOnly",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AllowStartStopOwn",
            "Effect": "Allow",
            "Action": [
                "ec2:StartInstances",
                "ec2:StopInstances"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CostExplorerRead",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyDestructive",
            "Effect": "Deny",
            "Action": [
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:RebootInstances",
                "cloudwatch:*"
            ],
            "Resource": "*"
        }
    ]
}
```

> ⚠️ **AWS Limitation:** IAM cannot filter `ec2:DescribeInstances` by tag.  
> At the AWS level, users CAN see all instances. Filtering by ownership happens in the **CloudSim backend** using the `CreatedBy` tag.

4. Name: `CloudSimUserPolicy`
5. Create policy

---

## Part 3: Create IAM User for Backend

### Step 3.1: Create User

1. Go to: https://console.aws.amazon.com/iam/home#/users
2. Click **Create user**
3. User name: `cloudsim-service`
4. Click **Next**
5. Select **Attach policies directly**
6. Search and check: `CloudSimAdminPolicy` (the backend needs full access to assume roles)
7. Click **Next** → **Create user**

### Step 3.2: Create Access Key

1. Click on `cloudsim-service` user
2. Go to **Security credentials** tab
3. Click **Create access key**
4. Select **Application running outside AWS**
5. Click **Next** → **Create access key**
6. **SAVE THESE KEYS!** 

```
Access key ID: AKIA...
Secret access key: wJalrXUtnFEMI...
```

### Step 3.3: Add STS Assume Role Permission

The backend user needs permission to assume roles. Add this inline policy:

1. On the user page, click **Add permissions** → **Create inline policy**
2. Select **JSON** tab
3. Paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAssumeCloudSimRoles",
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": [
                "arn:aws:iam::096615316348:role/CloudSimAdminRole",
                "arn:aws:iam::096615316348:role/CloudSimDevOpsRole",
                "arn:aws:iam::096615316348:role/CloudSimUserRole"
            ]
        }
    ]
}
```

4. Name: `AllowAssumeCloudSimRoles`
5. Create policy

---

## Part 4: Create IAM Roles

Create **3 roles** - one for each CloudSim user type.

### Step 4.1: Create Admin Role

1. Go to: https://console.aws.amazon.com/iam/home#/roles
2. Click **Create role**
3. Select **Custom trust policy**
4. Paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::096615316348:user/cloudsim-service"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

5. Click **Next**
6. Search and check: `CloudSimAdminPolicy`
7. Click **Next**
8. Role name: `CloudSimAdminRole`
9. Create role

### Step 4.2: Create DevOps Role

Repeat:
- Trust policy: Same as above
- Attach: `CloudSimDevOpsPolicy`
- Role name: `CloudSimDevOpsRole`

### Step 4.3: Create User Role

Repeat:
- Trust policy: Same as above
- Attach: `CloudSimUserPolicy`
- Role name: `CloudSimUserRole`

---

## Part 5: Configure CloudSim

### Step 5.1: Update AWS Credentials

```bash
aws configure
# Enter the new access key and secret from cloudsim-service user
```

Or update `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = AKIA...your-new-key...
aws_secret_access_key = wJalrXUtnFEMI...your-new-secret...
region = us-east-1
```

### Step 5.2: Update .env

```bash
# Enable role-based access
ENABLE_ROLE_BASED_ACCESS=true

# IAM Role ARNs
AWS_ROLE_ADMIN=arn:aws:iam::096615316348:role/CloudSimAdminRole
AWS_ROLE_DEVOPS=arn:aws:iam::096615316348:role/CloudSimDevOpsRole
AWS_ROLE_READONLY=arn:aws:iam::096615316348:role/CloudSimUserRole
```

### Step 5.3: Test Role Assumption

```bash
# Test assuming the admin role
aws sts assume-role \
    --role-arn arn:aws:iam::096615316348:role/CloudSimAdminRole \
    --role-session-name test-session

# Should return temporary credentials
```

---

## Summary: Role Mapping (per SRS Section 2.2)

| CloudSim User | Database Role | IAM Role | IAM Policy |
|---------------|---------------|----------|------------|
| admin@gmail.com | Admin | CloudSimAdminRole | CloudSimAdminPolicy |
| deng@gmail.com | DevOps Engineer | CloudSimDevOpsRole | CloudSimDevOpsPolicy |
| user@gmail.com | User | CloudSimUserRole | CloudSimUserPolicy |

---

## Permissions Summary

### AWS IAM Level

| Role | View Instances | Start/Stop | Reboot | Create | Terminate | Metrics | Costs |
|------|---------------|------------|--------|--------|-----------|---------|-------|
| User | ✅ All* | ✅ CloudSim only | ❌ | ❌ | ❌ | ❌ | ✅ |
| DevOps Engineer | ✅ All | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Admin | ✅ All | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> *AWS IAM cannot filter DescribeInstances by tag

### CloudSim Application Level (Additional Filtering)

| Role | View Instances | Start/Stop |
|------|---------------|------------|
| Admin | All | All |
| DevOps Engineer | All | All |
| User | Own only | Own only |


**How Instance Isolation Works:**
1. **Tagging**: Instances created via CloudSim are tagged with `CreatedBy=<user_id>`
2. **IAM Policy**: Limits Start/Stop to instances with `ManagedBy=CloudSim` tag
3. **Backend Filter**: `list_instances()` filters results by `CreatedBy` tag for User role
4. **Backend Check**: `start_instance()`/`stop_instance()` verify ownership for User role

---

*Reference: CloudSim SRS Section 2.2 - User Classes & Characteristics*
