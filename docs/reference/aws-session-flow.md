# CloudSim AWS Session & API Flow

This document explains how CloudSim obtains AWS credentials, creates sessions, and makes AWS API calls with role-based access control.

---

## Table of Contents

1. [Overview](#overview)
2. [Credential Chain](#credential-chain)
3. [Session Creation](#session-creation)
   - [Boto3 Session Setup](#boto3-session-setup)
   - [Default Clients](#default-clients)
   - [How is the Session Auto-Created?](#how-is-the-session-auto-created)
4. [Role-Based Access](#role-based-access)
5. [Complete Request Flow](#complete-request-flow)
6. [CLI Demonstration](#cli-demonstration)
7. [Code Reference](#code-reference)
8. [API Testing via Curl](#api-testing-via-curl)

---

## Overview

CloudSim uses a layered approach to AWS access:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CloudSim AWS Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────────┐    ┌───────────────────┐    │
│   │ Frontend │───▶│ Backend API  │───▶│ AWS Services      │    │
│   │ (React)  │    │ (FastAPI)    │    │ (EC2, CloudWatch) │    │
│   └──────────┘    └──────────────┘    └───────────────────┘    │
│                          │                      ▲              │
│                          ▼                      │              │
│                   ┌──────────────┐              │              │
│                   │ AWS Role     │──────────────┘              │
│                   │ Manager      │   (STS AssumeRole)          │
│                   └──────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Credential Chain

### Priority Order

CloudSim loads AWS credentials in this priority:

| Priority | Source | When Used |
|----------|--------|-----------|
| 1 | AWS Secrets Manager | Production (`ENVIRONMENT=production`) |
| 2 | `root-credentials/credentials` file | Development |
| 3 | Environment variables | Fallback |
| 4 | AWS profile (`~/.aws/credentials`) | Legacy |

### Production: AWS Secrets Manager

```python
# config.py - get_root_credentials()

def get_root_credentials() -> Tuple[str, str]:
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='prod/cloudsim')
    secret = json.loads(response['SecretString'])
    return secret['aws_access_key_id'], secret['aws_secret_access_key']
```

### Development: Local Credentials File

```python
# config.py - load_local_credentials()

def load_local_credentials() -> Tuple[Optional[str], Optional[str]]:
    # 1. Try root-credentials/credentials file
    creds_file = 'root-credentials/credentials'
    if os.path.exists(creds_file):
        config.read(creds_file)  # INI format
        if 'root' in config:
            return (
                config['root'].get('aws_access_key_id'),
                config['root'].get('aws_secret_access_key')
            )
    
    # 2. Fall back to environment variables
    return os.getenv('AWS_ACCESS_KEY_ID'), os.getenv('AWS_SECRET_ACCESS_KEY')
```

### Credentials File Format

```ini
# root-credentials/credentials
[root]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

---

## Session Creation

### Boto3 Session Setup

At application startup, CloudSim creates a boto3 session:

```python
# aws_service.py - _get_boto3_session()

def _get_boto3_session() -> boto3.Session:
    
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        # OPTION 1: Explicit credentials from .env
        return boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            region_name=settings.aws_region,
        )
    
    elif settings.aws_profile:
        # OPTION 2: Named AWS profile
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        )
    
    else:
        # OPTION 3: Default credential chain
        return boto3.Session(region_name=settings.aws_region)
```

### Default Clients

Created once at module import:

```python
# aws_service.py

_session = _get_boto3_session()
ec2 = _session.client("ec2")
ec2_resource = _session.resource("ec2")
cloudwatch = _session.client("cloudwatch")
cost_explorer = _session.client("ce", region_name="us-east-1")
```

### How is the Session Auto-Created?

The boto3 session is **automatically created at module import time** through Python's module initialization behavior. When Python imports a module, it executes all top-level code in that file.

#### The Import Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC SESSION CREATION FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. FastAPI starts (uvicorn app.main:app)                                   │
│     │                                                                       │
│     ▼                                                                       │
│  2. main.py is loaded                                                       │
│     │                                                                       │
│     │  from .ec2_routes import router as ec2_router                         │
│     ▼                                                                       │
│  3. ec2_routes.py is imported                                               │
│     │                                                                       │
│     │  from . import aws_service                                            │
│     ▼                                                                       │
│  4. aws_service.py is imported ← THIS TRIGGERS SESSION CREATION!            │
│     │                                                                       │
│     │  from .config import settings  ←─┐                                    │
│     │                                  │                                    │
│     ▼                                  │                                    │
│  5. config.py is imported              │                                    │
│     │                                  │                                    │
│     │  • load_local_credentials()      │ Returns settings with              │
│     │  • Settings class instantiated   │ aws_access_key_id, etc.            │
│     │  • settings = get_settings()     │                                    │
│     │                                  │                                    │
│     └──────────────────────────────────┘                                    │
│     │                                                                       │
│     ▼                                                                       │
│  6. Back in aws_service.py, these lines run:                                │
│                                                                             │
│     _session = _get_boto3_session()    # Creates boto3.Session              │
│     ec2 = _session.client("ec2")       # Creates EC2 client                 │
│     cloudwatch = _session.client("cloudwatch")                              │
│     cost_explorer = _session.client("ce")                                   │
│                                                                             │
│  7. Server is ready! All clients are pre-created.                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### The Trigger: main.py Imports

```python
# main.py (lines 30-33)

from .config import settings            # ← Triggers config.py import
from .auth_routes import router as auth_router
from .admin_routes import router as admin_router
from .ec2_routes import router as ec2_router  # ← This triggers aws_service.py import!
```

When `ec2_routes` is imported, it imports `aws_service`:

```python
# ec2_routes.py (line 43)

from . import aws_service  # ← This import triggers session creation!
```

#### Why This Design Pattern?

| Benefit | Explanation |
|---------|-------------|
| **Performance** | Clients are created once, reused for all requests |
| **Early Failure** | If credentials are wrong, app fails immediately at startup |
| **Simplicity** | No need to create clients in each request handler |
| **Thread Safety** | boto3 clients are thread-safe and can be safely shared |

This is a common Python pattern called **module-level initialization** or **singleton at import time**.

---

## Role-Based Access

When `ENABLE_ROLE_BASED_ACCESS=true`, CloudSim uses STS AssumeRole to give users different AWS permissions based on their CloudSim role.

### Role Mapping

| CloudSim Role | IAM Role ARN | Permissions |
|---------------|--------------|-------------|
| Admin | `CloudSimAdminRole` | Full EC2 + User Management |
| DevOps Engineer | `CloudSimDevOpsRole` | Full EC2 (including terminate) + CloudWatch + Cost Explorer |
| User | `CloudSimUserRole` | Manage (start/stop/reboot/terminate) own instances + own metrics |

### Configuration (.env)

```env
ENABLE_ROLE_BASED_ACCESS=true
AWS_ROLE_ADMIN=arn:aws:iam::096615316348:role/CloudSimAdminRole
AWS_ROLE_DEVOPS=arn:aws:iam::096615316348:role/CloudSimDevOpsRole
AWS_ROLE_READONLY=arn:aws:iam::096615316348:role/CloudSimUserRole
```

### AssumeRole Flow

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ User Request │───▶│ get_aws_client   │───▶│ STS AssumeRole  │
│ (role=User)  │    │ _for_user()      │    │                 │
└──────────────┘    └──────────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │ Map role to ARN: │    │ Temp Credentials│
                    │ User → UserRole  │    │ (1 hour valid)  │
                    └──────────────────┘    └─────────────────┘
```

### Code: Role Mapping

```python
# aws_role_manager.py - get_role_arn_for_user()

def get_role_arn_for_user(user_role: str) -> Optional[str]:
    if not settings.enable_role_based_access:
        return None
    
    role_mapping = {
        'Admin': settings.aws_role_admin,
        'DevOps Engineer': settings.aws_role_devops,
        'User': settings.aws_role_readonly,
    }
    
    return role_mapping.get(user_role)
```

### Code: Assuming the Role

```python
# aws_role_manager.py - assume_role()

def assume_role(self, role_arn: str, session_name: str, duration: int = 3600):
    response = self.sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=duration
    )
    
    return response['Credentials']
    # Returns:
    # {
    #   'AccessKeyId': 'ASIA...',
    #   'SecretAccessKey': '...',
    #   'SessionToken': '...',
    #   'Expiration': datetime
    # }
```

### Code: Creating Client with Temp Credentials

```python
# aws_role_manager.py - get_service_client()

def get_service_client(self, service: str, role_arn: str, session_name: str):
    credentials = self.assume_role(role_arn, session_name)
    
    return boto3.client(
        service,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=settings.aws_region,
    )
```

---

## Complete Request Flow

### Example: user@gmail.com Lists EC2 Instances

#### Phase 1: Authentication

```
Browser                              Backend
   │                                    │
   │  POST /api/auth/login              │
   │  username=user@gmail.com           │
   │  password=user123                  │
   │ ──────────────────────────────────▶│
   │                                    │
   │                          ┌─────────┴─────────┐
   │                          │ 1. Query DB       │
   │                          │ 2. Verify bcrypt  │
   │                          │ 3. Create JWT     │
   │                          └─────────┬─────────┘
   │                                    │
   │  {"access_token": "eyJ...",        │
   │   "token_type": "bearer"}          │
   │ ◀──────────────────────────────────│
```

#### Phase 2: API Request

```
Browser                              Backend
   │                                    │
   │  GET /api/ec2/instances            │
   │  Authorization: Bearer eyJ...      │
   │ ──────────────────────────────────▶│
   │                                    │
   │                          ┌─────────┴─────────┐
   │                          │ get_current_user()│
   │                          │ 1. Decode JWT     │
   │                          │ 2. Extract email  │
   │                          │ 3. Query DB       │
   │                          │ 4. Return User    │
   │                          └─────────┬─────────┘
   │                                    │
   │                          ┌─────────┴─────────┐
   │                          │ list_instances()  │
   │                          │ 1. Call AWS EC2   │
   │                          │ 2. Filter by role │
   │                          └─────────┬─────────┘
   │                                    │
   │  [{"instance_id": "i-xxx", ...}]   │
   │ ◀──────────────────────────────────│
```

#### Phase 3: AWS API Call

```python
# ec2_routes.py - list_instances endpoint

@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user),  # JWT validation
    db: Session = Depends(get_db)
):
    # 1. Fetch ALL instances from AWS
    instances = aws_service.list_instances()
    
    # 2. Sync to local database (for caching)
    sync_instances_to_db(instances, db)
    
    # 3. Filter based on user role
    filtered = _filter_instances_for_user(instances, current_user)
    
    return filtered
```

#### Phase 4: Instance Filtering

```python
# ec2_routes.py - _filter_instances_for_user()

def _filter_instances_for_user(instances: list, user: User) -> list:
    
    # Admin/DevOps see all instances
    if user.role in ["Admin", "DevOps Engineer"]:
        return instances
    
    # User role: filter by CreatedBy tag
    filtered = []
    for inst in instances:
        for tag in inst.get("tags", []):
            if tag.get("Key") == "CreatedBy":
                if tag.get("Value") == str(user.id):
                    filtered.append(inst)
    
    return filtered
```

---

## CLI Demonstration

### Check AWS Configuration

```bash
# Show current credentials
aws configure list

# Verify identity
aws sts get-caller-identity
```

### Test AssumeRole

```bash
# Assume Admin role
aws sts assume-role \
  --role-arn "arn:aws:iam::096615316348:role/CloudSimAdminRole" \
  --role-session-name "test-admin"

# Assume DevOps role
aws sts assume-role \
  --role-arn "arn:aws:iam::096615316348:role/CloudSimDevOpsRole" \
  --role-session-name "test-devops"

# Assume User role
aws sts assume-role \
  --role-arn "arn:aws:iam::096615316348:role/CloudSimUserRole" \
  --role-session-name "test-user"
```

### Use Assumed Role Credentials

```bash
# Get credentials
CREDS=$(aws sts assume-role \
  --role-arn "arn:aws:iam::096615316348:role/CloudSimAdminRole" \
  --role-session-name "demo" \
  --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
  --output text)

# Parse credentials
read KEY SECRET TOKEN <<< "$CREDS"

# Make API call with assumed role
AWS_ACCESS_KEY_ID="$KEY" \
AWS_SECRET_ACCESS_KEY="$SECRET" \
AWS_SESSION_TOKEN="$TOKEN" \
  aws ec2 describe-instances
```

### Test EC2 Operations

```bash
# List regions
aws ec2 describe-regions --query "Regions[*].RegionName" --output table

# List instances
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,Tags[?Key=='Name'].Value|[0],State.Name]" \
  --output table

# List available instance types
aws ec2 describe-instance-types \
  --instance-types t2.micro t2.small t2.medium \
  --query "InstanceTypes[*].[InstanceType,VCpuInfo.DefaultVCpus,MemoryInfo.SizeInMiB]" \
  --output table
```

---

## Code Reference

### Key Files

| File | Purpose |
|------|---------|
| `config.py` | Loads credentials and settings from .env |
| `aws_service.py` | Boto3 session and EC2/CloudWatch/Cost Explorer operations |
| `aws_role_manager.py` | STS AssumeRole and credential caching |
| `auth.py` | JWT token creation and validation |
| `ec2_routes.py` | EC2 API endpoints with access control |

### Settings (.env)

```env
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://postgres:1@localhost:5432/cloudsim

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=096615316348

# Role-Based Access (optional)
ENABLE_ROLE_BASED_ACCESS=true
AWS_ROLE_ADMIN=arn:aws:iam::096615316348:role/CloudSimAdminRole
AWS_ROLE_DEVOPS=arn:aws:iam::096615316348:role/CloudSimDevOpsRole
AWS_ROLE_READONLY=arn:aws:iam::096615316348:role/CloudSimUserRole
```

### IAM Role Trust Policy

For AssumeRole to work, each IAM role needs a trust policy:

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

---

## Summary

1. **Credentials loaded at startup** from Secrets Manager (prod) or local file (dev)
2. **Boto3 session created** with credentials
3. **Default clients created** for EC2, CloudWatch, Cost Explorer
4. **Per-request**: JWT validated → User fetched → Role determined
5. **Role-based access**: If enabled, STS AssumeRole creates temp credentials
6. **AWS API call** made with appropriate permissions
7. **Results filtered** based on user role and ownership tags

---

---

## API Testing via Curl

Test the role-based access control by logging in as different users and making API calls.

### 1. Get Access Tokens

First, obtain JWT tokens for each role:

```bash
# Admin Token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=admin@gmail.com&password=1" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# DevOps Token
DEVOPS_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=deng@gmail.com&password=1" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# User Token
USER_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=user@gmail.com&password=1" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
```

### 2. Test List Instances (Read Access)

All roles should be able to list instances, but Users will only see their own.

```bash
echo "--- ADMIN VIEW ---"
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/ec2/instances | json_pp

echo "--- USER VIEW ---"
curl -s -H "Authorization: Bearer $USER_TOKEN" http://localhost:8000/api/ec2/instances | json_pp
```

### 3. Test Terminate Instance

Admin and DevOps Engineer can terminate any instance. User can only terminate their own instances.

```bash
# Replace i-xxxxxxxx with a real instance ID
INSTANCE_ID="i-0abc123def456"

# Try as USER on instance they DON'T own (Should Fail - 403 Forbidden)
curl -X DELETE -H "Authorization: Bearer $USER_TOKEN" \
  http://localhost:8000/api/ec2/instances/$INSTANCE_ID

# Try as DEVOPS (Should Succeed)
curl -X DELETE -H "Authorization: Bearer $DEVOPS_TOKEN" \
  http://localhost:8000/api/ec2/instances/$INSTANCE_ID

# Try as ADMIN (Should Succeed)
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/ec2/instances/$INSTANCE_ID
```
