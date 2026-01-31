# CloudSim Backend Learning Guide

A comprehensive guide to Python backend development for aspiring fullstack engineers, using the CloudSim project as a reference implementation. Includes interview preparation and hands-on exercises.

---

## Table of Contents

1.  [Technology Stack Overview](#technology-stack-overview)
2.  [Python Fundamentals for Backend](#python-fundamentals-for-backend)
3.  [FastAPI Core Concepts](#fastapi-core-concepts)
4.  [Pydantic Data Validation](#pydantic-data-validation)
5.  [SQLAlchemy ORM](#sqlalchemy-orm)
6.  [Authentication with JWT](#authentication-with-jwt)
7.  [AWS Integration with boto3](#aws-integration-with-boto3)
8.  [API Design Patterns](#api-design-patterns)
9.  [Error Handling & Logging](#error-handling--logging)
10. [Interview Questions & Answers](#interview-questions--answers)
11. [Hands-On Exercises (CloudSim-Based)](#hands-on-exercises-cloudsim-based)
12. [Best Learning Resources](#best-learning-resources)

---

## Technology Stack Overview

The CloudSim backend uses a production-ready Python stack:

| Technology | Purpose | Version |
|------------|---------|---------|
| **FastAPI** | Web framework (async, modern) | 0.104+ |
| **Pydantic** | Data validation & serialization | 2.0+ |
| **SQLAlchemy** | ORM (Object-Relational Mapper) | 2.0+ |
| **PostgreSQL** | Relational database | 15+ |
| **boto3** | AWS SDK for Python | 1.34+ |
| **python-jose** | JWT token handling | 3.3+ |
| **passlib** | Password hashing (bcrypt) | 1.7+ |
| **uvicorn** | ASGI server | 0.24+ |

**📂 CloudSim Reference:** `backend/requirements.txt`

---

## Python Fundamentals for Backend

### Type Hints (Essential for FastAPI)

Python type hints make code self-documenting and enable FastAPI's automatic validation:

```python
# CloudSim: backend/app/aws_service.py
def get_instance(instance_id: str) -> Optional[dict]:
    """Get detailed information for a specific instance."""
    # Type hint: takes str, returns dict or None
    ...
```

| Type Hint | Meaning | Example |
|-----------|---------|---------|
| `str` | String | `name: str` |
| `int` | Integer | `count: int` |
| `bool` | Boolean | `is_active: bool` |
| `list[str]` | List of strings | `tags: list[str]` |
| `dict` | Dictionary | `data: dict` |
| `Optional[str]` | String or None | `public_ip: Optional[str]` |

### Async/Await (Concurrent Operations)

FastAPI supports async functions for non-blocking I/O:

```python
# CloudSim: backend/app/ec2_routes.py
@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user)
):
    """Async endpoint - doesn't block other requests while waiting for AWS."""
    instances = aws_service.list_instances()
    return instances
```

**When to use async:**
- API calls that wait for external services (AWS, databases)
- File I/O operations
- Network requests

**📚 Resources:**
- [Python Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [Async Python Tutorial](https://realpython.com/async-io-python/)

---

## FastAPI Core Concepts

### What is FastAPI?
FastAPI is a modern, high-performance Python web framework built on:
- **Starlette** (async web server)
- **Pydantic** (data validation)
- Automatic **OpenAPI/Swagger** documentation

### Application Setup

```python
# CloudSim: backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI application
app = FastAPI(title="CloudSim API", version="1.0.0")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Include routers (modular organization)
app.include_router(auth_router)
app.include_router(ec2_router)
```

### Routers (Modular Organization)

Routers group related endpoints:

```python
# CloudSim: backend/app/ec2_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/ec2", tags=["EC2"])

@router.get("/instances")
async def list_instances():
    """GET /api/ec2/instances"""
    return aws_service.list_instances()

@router.post("/instances")
async def create_instance(request: CreateInstanceRequest):
    """POST /api/ec2/instances"""
    return aws_service.create_instance(request.name)
```

### Path Parameters & Query Parameters

```python
# Path parameter: /api/ec2/instances/{instance_id}
@router.get("/instances/{instance_id}")
async def get_instance(instance_id: str):
    return aws_service.get_instance(instance_id)

# Query parameter: /api/ec2/instances/{id}/metrics?period=60
@router.get("/instances/{instance_id}/metrics")
async def get_metrics(
    instance_id: str,       # Path parameter
    period: int = 60        # Query parameter with default
):
    return aws_service.get_instance_metrics(instance_id, period)
```

### Dependency Injection

FastAPI's `Depends()` allows reusable components:

```python
# CloudSim: backend/app/ec2_routes.py
from fastapi import Depends

@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user),  # Auth dependency
    db: Session = Depends(get_db)                     # DB session dependency
):
    # current_user and db are automatically injected
    instances = aws_service.list_instances()
    sync_instances_to_db(instances, db)
    return instances
```

**Common Dependencies in CloudSim:**
- `get_current_user` - Validates JWT and returns User
- `get_db` - Provides database session

**📂 CloudSim Reference:** `backend/app/main.py`, `backend/app/ec2_routes.py`

**📚 Resources:**
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [FastAPI Tutorial (Video)](https://www.youtube.com/watch?v=0sOvCWFHLMs)

---

## Pydantic Data Validation

### What is Pydantic?
Pydantic provides automatic data validation using Python type hints. FastAPI uses it for request/response validation.

### Request Models (Input Validation)

```python
# CloudSim: backend/app/ec2_routes.py
from pydantic import BaseModel

class CreateInstanceRequest(BaseModel):
    name: str                          # Required
    instance_type: str = "t2.micro"    # Optional with default

# FastAPI automatically validates incoming JSON
@router.post("/instances")
async def create_instance(request: CreateInstanceRequest):
    # If name is missing, FastAPI returns 422 error automatically
    return aws_service.create_instance(request.name, request.instance_type)
```

### Response Models (Output Serialization)

```python
# CloudSim: backend/app/ec2_routes.py
class InstanceResponse(BaseModel):
    instance_id: str
    name: str
    instance_type: str
    state: str
    public_ip: Optional[str]      # Can be None
    private_ip: Optional[str]
    launch_time: Optional[str]
    availability_zone: str

# response_model ensures consistent output format
@router.get("/instances", response_model=list[InstanceResponse])
async def list_instances():
    return aws_service.list_instances()
```

### Nested Models

```python
# CloudSim: backend/app/ec2_routes.py
class SecurityGroup(BaseModel):
    GroupId: str
    GroupName: str

class BlockDevice(BaseModel):
    device_name: str
    volume_id: str
    size: int
    volume_type: str
    encrypted: bool

class InstanceDetailResponse(InstanceResponse):
    security_groups: list[SecurityGroup] = []  # Nested list
    block_devices: list[BlockDevice] = []
    tags: list[Tag] = []
```

### Email Validation

```python
# CloudSim: backend/app/auth.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr  # Validates email format automatically
    password: str
```

**📂 CloudSim Reference:** `backend/app/ec2_routes.py`, `backend/app/auth.py`

**📚 Resources:**
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## SQLAlchemy ORM

### What is an ORM?
ORM (Object-Relational Mapper) lets you interact with databases using Python objects instead of SQL.

### Database Connection Setup

```python
# CloudSim: backend/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1@localhost:5432/cloudsim")

# Engine manages the connection pool
engine = create_engine(DATABASE_URL, echo=False, future=True)

# SessionLocal creates database sessions
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# Base class for all models
Base = declarative_base()

# Dependency for FastAPI route handlers
def get_db():
    """Yield a database session, auto-close when done."""
    db = SessionLocal()
    try:
        yield db  # FastAPI calls this in Depends()
    finally:
        db.close()
```

### Defining Models

```python
# CloudSim: backend/app/models.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"  # Database table name

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="User")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Instance(Base):
    __tablename__ = "instances"

    instance_id = Column(String, primary_key=True, index=True)  # AWS instance ID
    name = Column(String, nullable=True)
    instance_type = Column(String, nullable=False)
    state = Column(String, default="pending")
    public_ip = Column(String, nullable=True)
    private_ip = Column(String, nullable=True)
    availability_zone = Column(String, nullable=True)
    launch_time = Column(DateTime, nullable=True)
    last_synced = Column(DateTime, default=datetime.utcnow)
```

### CRUD Operations

```python
# CloudSim: backend/app/ec2_routes.py

# CREATE
db_instance = Instance(instance_id="i-123", name="web-server")
db.add(db_instance)
db.commit()
db.refresh(db_instance)  # Reload from DB

# READ (Query)
user = db.query(User).filter(User.email == "test@example.com").first()
instances = db.query(Instance).all()
instance = db.query(Instance).filter(Instance.instance_id == "i-123").first()

# UPDATE
db_instance.state = "running"
db.commit()

# DELETE
db.delete(db_instance)
db.commit()
```

### Auto-Create Tables

```python
# CloudSim: backend/app/main.py
from .db import engine, Base

# Create all tables on startup (simple approach)
Base.metadata.create_all(bind=engine)
```

**📂 CloudSim Reference:** `backend/app/db.py`, `backend/app/models.py`

**📚 Resources:**
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [FastAPI + SQLAlchemy Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)

---

## Authentication with JWT

### What is JWT?
JWT (JSON Web Token) is a self-contained token for stateless authentication:
- **Stateless**: No server-side session storage needed
- **Scalable**: Works across multiple servers
- **Self-contained**: Contains user info in the token itself

### Token Structure

```
Header.Payload.Signature
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzA0MTIzNDU2fQ.signature
```

### Password Hashing with bcrypt

```python
# CloudSim: backend/app/auth.py
from passlib.context import CryptContext

# Create password context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using constant-time comparison."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password with auto-generated salt."""
    return pwd_context.hash(password)
```

### Creating JWT Tokens

```python
# CloudSim: backend/app/auth.py
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"  # In production: use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Protecting Routes with Dependencies

```python
# CloudSim: backend/app/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to validate JWT and return current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user
```

### Using in Routes

```python
# CloudSim: backend/app/ec2_routes.py
@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user)  # Protected!
):
    # Only authenticated users can access this
    return aws_service.list_instances()
```

**📂 CloudSim Reference:** `backend/app/auth.py`, `backend/app/auth_routes.py`

**📚 Resources:**
- [JWT Introduction](https://jwt.io/introduction)
- [FastAPI Security Guide](https://fastapi.tiangolo.com/tutorial/security/)

---

## AWS Integration with boto3

### What is boto3?
boto3 is the official AWS SDK for Python. It provides Python APIs for all AWS services.

### Client Setup

```python
# CloudSim: backend/app/aws_service.py
import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Client for API calls (low-level)
ec2 = boto3.client("ec2", region_name=AWS_REGION)

# Resource for object-oriented interface (high-level)
ec2_resource = boto3.resource("ec2", region_name=AWS_REGION)
```

### Common EC2 Operations

```python
# CloudSim: backend/app/aws_service.py

# List instances
def list_instances() -> list[dict]:
    response = ec2.describe_instances()
    instances = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instances.append({
                "instance_id": instance["InstanceId"],
                "state": instance["State"]["Name"],
                "instance_type": instance["InstanceType"],
            })
    return instances

# Start instance
def start_instance(instance_id: str) -> dict:
    ec2.start_instances(InstanceIds=[instance_id])
    return {"message": f"Starting {instance_id}", "instance_id": instance_id}

# Stop instance
def stop_instance(instance_id: str) -> dict:
    ec2.stop_instances(InstanceIds=[instance_id])
    return {"message": f"Stopping {instance_id}", "instance_id": instance_id}

# Create instance
def create_instance(name: str, instance_type: str = "t2.micro") -> dict:
    response = ec2_resource.create_instances(
        ImageId="ami-12345",
        InstanceType=instance_type,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": name}]
        }]
    )
    return {"instance_id": response[0].id}
```

### Error Handling

```python
# CloudSim: backend/app/aws_service.py
from botocore.exceptions import ClientError

def stop_instance(instance_id: str) -> dict:
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
        return {"message": f"Stopping {instance_id}"}
    except ClientError as e:
        raise Exception(f"Failed to stop instance: {e}")
```

### CloudWatch Metrics

```python
# CloudSim: backend/app/aws_service.py
cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)

def get_instance_metrics(instance_id: str, period_minutes: int = 60) -> dict:
    from datetime import datetime, timedelta
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=period_minutes)
    
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,  # 5-minute intervals
        Statistics=["Average"],
    )
    return response.get("Datapoints", [])
```

**📂 CloudSim Reference:** `backend/app/aws_service.py`

**📚 Resources:**
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS SDK for Python Quickstart](https://aws.amazon.com/sdk-for-python/)

---

## API Design Patterns

### RESTful URL Structure

```
GET    /api/ec2/instances              # List all
GET    /api/ec2/instances/{id}         # Get one
POST   /api/ec2/instances              # Create
PUT    /api/ec2/instances/{id}         # Update (full)
PATCH  /api/ec2/instances/{id}         # Update (partial)
DELETE /api/ec2/instances/{id}         # Delete

# Actions (non-CRUD)
POST   /api/ec2/instances/{id}/start   # Action: Start
POST   /api/ec2/instances/{id}/stop    # Action: Stop
POST   /api/ec2/instances/{id}/reboot  # Action: Reboot
```

### Role-Based Access Control (RBAC)

```python
# CloudSim: backend/app/ec2_routes.py
@router.post("/instances")
async def create_instance(
    request: CreateInstanceRequest,
    current_user: User = Depends(get_current_user)
):
    # Check role before action
    if current_user.role not in ["Admin", "DevOps Engineer"]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to create instances"
        )
    return aws_service.create_instance(request.name)


@router.delete("/instances/{instance_id}")
async def terminate_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    # Admin-only action
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to terminate instances"
        )
    return aws_service.terminate_instance(instance_id)
```

### Consistent Response Format

```python
# Success responses
{"message": "Instance created", "instance_id": "i-123"}
{"data": [...], "count": 5}

# Error responses
{"detail": "Instance not found"}
{"detail": "Insufficient permissions"}
```

---

## Error Handling & Logging

### FastAPI HTTP Exceptions

```python
# CloudSim: backend/app/ec2_routes.py
from fastapi import HTTPException

@router.get("/instances/{instance_id}")
async def get_instance(instance_id: str):
    instance = aws_service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Instance not found"
        )
    
    return instance
```

### Try/Except Pattern

```python
# CloudSim: backend/app/ec2_routes.py
@router.post("/instances/{instance_id}/start")
async def start_instance(instance_id: str):
    try:
        return aws_service.start_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful GET/PUT |
| 201 | Created | Successful POST (create) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Valid token, wrong role |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable | Pydantic validation failed |
| 500 | Internal Error | Server-side exception |

---

## Interview Questions & Answers

### 🔵 Python Backend Questions

#### Q1: What is the difference between `==` and `is` in Python?
**Answer:**
- `==` compares **values** (equality)
- `is` compares **identity** (same object in memory)

```python
a = [1, 2, 3]
b = [1, 2, 3]
a == b  # True (same values)
a is b  # False (different objects)
```

#### Q2: What are decorators and how are they used in FastAPI?
**Answer:** Decorators wrap functions to add behavior. FastAPI uses them for routing:

```python
@router.get("/instances")  # Decorator registers this as a GET endpoint
async def list_instances():
    return []
```

**CloudSim Example:** Every route in `ec2_routes.py` uses decorators.

---

#### Q3: Explain the difference between sync and async functions
**Answer:**
- **Sync:** Blocks execution until complete
- **Async:** Allows other code to run while waiting

```python
# Sync - blocks
def fetch_data():
    return requests.get(url)

# Async - non-blocking
async def fetch_data():
    return await httpx.get(url)
```

**When to use async:** I/O operations (database, API calls, file operations)

---

#### Q4: What is dependency injection in FastAPI?
**Answer:** Dependencies are reusable components injected into route handlers:

```python
# CloudSim Example
@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user),  # Auth injected
    db: Session = Depends(get_db)                     # DB session injected
):
    ...
```

**Benefits:** Reusability, testability, separation of concerns

---

#### Q5: How does JWT authentication work?
**Answer:**
1. User sends credentials to `/login`
2. Server validates and returns JWT token
3. Client stores token and sends with each request
4. Server validates token on protected routes

**CloudSim Flow:**
1. `POST /api/auth/login` → Returns `{"access_token": "eyJ..."}`
2. Client sends `Authorization: Bearer eyJ...`
3. `get_current_user` dependency validates token

---

#### Q6: What is the N+1 query problem and how do you solve it?
**Answer:** N+1 occurs when you query a list (1 query), then query related data for each item (N queries).

**Solution:** Use eager loading (SQLAlchemy `joinedload`):
```python
# Bad: N+1 problem
users = db.query(User).all()
for user in users:
    print(user.instances)  # Separate query for each user!

# Good: Eager loading
from sqlalchemy.orm import joinedload
users = db.query(User).options(joinedload(User.instances)).all()
```

---

#### Q7: Explain the Repository pattern
**Answer:** Repository pattern separates data access from business logic:

```python
# Repository (data layer)
class InstanceRepository:
    def get_all(self, db: Session):
        return db.query(Instance).all()
    
    def get_by_id(self, db: Session, instance_id: str):
        return db.query(Instance).filter(Instance.instance_id == instance_id).first()

# Service (business logic)
class InstanceService:
    def __init__(self, repo: InstanceRepository):
        self.repo = repo
    
    def list_running(self, db: Session):
        instances = self.repo.get_all(db)
        return [i for i in instances if i.state == "running"]
```

**CloudSim uses:** Service layer pattern in `aws_service.py`

---

### 🟢 Fullstack Questions

#### Q8: How do you handle CORS in FastAPI?
**Answer:** Use CORSMiddleware:

```python
# CloudSim: backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

#### Q9: Describe the request lifecycle in CloudSim
**Answer:**
1. **Frontend:** User clicks "Start Instance"
2. **Axios:** Sends `POST /api/ec2/instances/{id}/start`
3. **CORS:** Middleware validates origin
4. **Auth:** `get_current_user` validates JWT
5. **Route:** `start_instance()` handler executes
6. **Service:** `aws_service.start_instance()` calls AWS
7. **Response:** JSON returned to frontend
8. **UI:** Toast notification shown

---

#### Q10: How do you secure API keys and secrets?
**Answer:**
1. **Environment variables** - Never hardcode secrets
2. **`.env` files** - Local development (gitignored)
3. **AWS credentials** - Use `~/.aws/credentials` or IAM roles
4. **Production** - Use secrets manager (AWS Secrets Manager, Vault)

**CloudSim Pattern:**
```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-key")
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

## Hands-On Exercises (CloudSim-Based)

### Exercise 1: Add Instance Tag Endpoint (Basic CRUD)
**Difficulty:** ⭐ Easy | **Concepts:** Routes, Pydantic, AWS

**Task:** Add an endpoint to add a tag to an instance.

**Steps:**
1. Create Pydantic schema in `ec2_routes.py`:
```python
class AddTagRequest(BaseModel):
    key: str
    value: str
```

2. Add route:
```python
@router.post("/instances/{instance_id}/tags")
async def add_instance_tag(
    instance_id: str,
    request: AddTagRequest,
    current_user: User = Depends(get_current_user)
):
    ec2.create_tags(
        Resources=[instance_id],
        Tags=[{"Key": request.key, "Value": request.value}]
    )
    return {"message": f"Tag added to {instance_id}"}
```

**Interview Connection:** "Describe how you'd extend an API with a new endpoint."

---

### Exercise 2: Implement Password Reset (Auth Flow)
**Difficulty:** ⭐⭐ Medium | **Concepts:** JWT, Email, Security

**Task:** Add password reset functionality.

**Steps:**
1. Add `POST /api/auth/forgot-password` - generates reset token
2. Add `POST /api/auth/reset-password` - validates token, updates password
3. Store reset token in DB with expiration

**Starter Code:**
```python
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        token = create_access_token({"sub": user.email}, expires_delta=timedelta(hours=1))
        # In production: send email with token
        return {"message": "Reset email sent", "token": token}  # Dev only!
    return {"message": "If email exists, reset link sent"}
```

**Interview Connection:** "How would you implement a secure password reset flow?"

---

### Exercise 3: Add Request Logging Middleware
**Difficulty:** ⭐⭐ Medium | **Concepts:** Middleware, Logging

**Task:** Log all incoming requests with timing.

**Steps:**
1. Create middleware in `main.py`:
```python
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
    return response
```

**Interview Connection:** "How do you implement observability in APIs?"

---

### Exercise 4: Rate Limiting
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Middleware, Redis, Security

**Task:** Implement rate limiting (60 requests/minute per IP).

**Steps:**
1. Install Redis: `pip install redis`
2. Create rate limit middleware
3. Track requests per IP with TTL

**Starter Code:**
```python
from datetime import datetime
import redis

r = redis.Redis(host='localhost', port=6379)

async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    current = r.get(key)
    if current and int(current) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    r.incr(key)
    r.expire(key, 60)  # Reset after 60 seconds
    
    return await call_next(request)
```

**Interview Connection:** "How would you prevent API abuse?"

---

### Exercise 5: Background Job Queue
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Celery, Async, Workers

**Task:** Move instance creation to a background job.

**Steps:**
1. Install Celery: `pip install celery redis`
2. Create `tasks.py` with Celery app
3. Modify `create_instance` to queue task instead of waiting

**Starter Code:**
```python
# tasks.py
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def create_instance_task(name: str, instance_type: str):
    return aws_service.create_instance(name, instance_type)

# In route:
@router.post("/instances")
async def create_instance(request: CreateInstanceRequest):
    task = create_instance_task.delay(request.name, request.instance_type)
    return {"task_id": task.id, "status": "queued"}
```

**Interview Connection:** "How do you handle long-running operations in an API?"

---

### Exercise 6: API Versioning
**Difficulty:** ⭐⭐ Medium | **Concepts:** API Design, Routing

**Task:** Add API versioning support (`/api/v1/...`, `/api/v2/...`).

**Steps:**
1. Create version-prefixed routers:
```python
router_v1 = APIRouter(prefix="/api/v1")
router_v2 = APIRouter(prefix="/api/v2")

# In main.py
app.include_router(ec2_router_v1)
app.include_router(ec2_router_v2)
```

**Interview Connection:** "How do you handle API versioning and backwards compatibility?"

---

### Exercise 7: Database Migrations with Alembic
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Database, Migrations

**Task:** Set up Alembic for database migrations instead of `create_all`.

**Steps:**
1. Install: `pip install alembic`
2. Initialize: `alembic init alembic`
3. Configure `alembic.ini` and `env.py`
4. Generate migration: `alembic revision --autogenerate -m "initial"`
5. Apply: `alembic upgrade head`

**Interview Connection:** "How do you manage database schema changes in production?"

---

### Exercise 8: Unit Testing with pytest
**Difficulty:** ⭐⭐ Medium | **Concepts:** Testing, Mocking

**Task:** Write tests for `aws_service.py` functions.

**Steps:**
1. Create `tests/test_aws_service.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from app.aws_service import list_instances

@patch('app.aws_service.ec2')
def test_list_instances(mock_ec2):
    # Mock AWS response
    mock_ec2.describe_instances.return_value = {
        "Reservations": [{
            "Instances": [{
                "InstanceId": "i-123",
                "InstanceType": "t2.micro",
                "State": {"Name": "running"},
                "Placement": {"AvailabilityZone": "us-east-1a"},
                "Tags": [{"Key": "Name", "Value": "test"}]
            }]
        }]
    }
    
    result = list_instances()
    
    assert len(result) == 1
    assert result[0]["instance_id"] == "i-123"
    assert result[0]["state"] == "running"
```

**Interview Connection:** "How do you test code that depends on external services?"

---

## Exercise Progress Tracker

| # | Exercise | Status | Concepts Practiced |
|---|----------|--------|-------------------|
| 1 | Add Tag Endpoint | ☐ | Routes, Pydantic, AWS |
| 2 | Password Reset | ☐ | JWT, Security |
| 3 | Request Logging | ☐ | Middleware, Logging |
| 4 | Rate Limiting | ☐ | Redis, Security |
| 5 | Background Jobs | ☐ | Celery, Async |
| 6 | API Versioning | ☐ | API Design |
| 7 | DB Migrations | ☐ | Alembic, Database |
| 8 | Unit Testing | ☐ | pytest, Mocking |

---

## Best Learning Resources

### Free Courses
1. **[FastAPI Official Tutorial](https://fastapi.tiangolo.com/tutorial/)** - Start here
2. **[Real Python](https://realpython.com/)** - In-depth Python tutorials
3. **[SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)**

### Video Tutorials
1. **[FastAPI Full Course (FreeCodeCamp)](https://www.youtube.com/watch?v=0sOvCWFHLMs)** - 19 hours
2. **[Corey Schafer Flask Series](https://www.youtube.com/playlist?list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH)** - Concepts apply to FastAPI
3. **[Tech With Tim Python Backend](https://www.youtube.com/c/TechWithTim)**

### Documentation (Keep Bookmarked)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [boto3 Docs](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

### Books
- **"Architecture Patterns with Python"** - Domain-Driven Design
- **"Two Scoops of Django"** - Best practices (applicable to FastAPI)

---

## Quick Reference: CloudSim Backend File Map

```
backend/
├── requirements.txt              # Python dependencies
└── app/
    ├── __init__.py               # Package marker
    ├── main.py                   # FastAPI app, CORS, router inclusion
    ├── db.py                     # Database connection, session management
    ├── models.py                 # SQLAlchemy models (User, Instance)
    ├── auth.py                   # JWT utilities, password hashing, get_current_user
    ├── auth_routes.py            # /api/auth/* endpoints (login, register)
    ├── admin_routes.py           # /api/admin/* endpoints (user management)
    ├── ec2_routes.py             # /api/ec2/* endpoints (instances, metrics, costs)
    └── aws_service.py            # boto3 wrapper for EC2, CloudWatch, Cost Explorer
```

---

## Running the Backend

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source ../.venv/bin/activate  # Linux/Mac
# or: ..\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:5432/cloudsim"
export AWS_REGION="us-east-1"

# Run development server
uvicorn app.main:app --reload --port 8000

# Access API docs
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

---

*Generated for CloudSim - A cloud infrastructure management application built with FastAPI, SQLAlchemy, and AWS boto3.*
