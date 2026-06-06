# CloudSim Roles Reference

Last updated: June 6, 2026

CloudSim has three application roles: `Admin`, `DevOps Engineer`, and `User`.
The authoritative role is stored on the PostgreSQL `users` row.

The login JWT contains only the user's email as its subject. On every protected
request, FastAPI decodes that email and reloads the current user, role, and
active status from PostgreSQL. Role changes, deactivation, and deletion
therefore take effect on the next API request.

## Effective Authorization

Effective access depends on three layers:

1. Application RBAC and ownership checks in FastAPI.
2. The selected service mode: `mock` or `live`.
3. In live mode, the permissions of the shared backend credentials or optional
   STS-assumed IAM role.

AWS IAM does not replace backend authorization. When role-based AWS access is
enabled, effective access is the intersection of CloudSim's route checks and the
mapped IAM policy.

## Application Permission Matrix

| Action | Admin | DevOps Engineer | User |
| :--- | :---: | :---: | :---: |
| Register through public signup | Yes, but new account is always `User` | Yes, but new account is always `User` | Yes |
| View instance list | All visible instances | All visible instances | Owned instances only |
| View instance details | Any instance | Any instance | Owned instances only |
| Load launch options | Yes | Yes | Yes |
| Launch instance | Yes | Yes | Yes, owned by the current user |
| Start / stop / reboot / terminate | Any instance | Any instance | Owned instances only |
| View CPU / network / disk metrics | Any instance | Any instance | Owned instances only |
| View costs | Full scope | Full scope | Owned/scoped costs |
| List / create / update / deactivate / delete users through admin API | Yes | No | No |

All instance, metric, cost, launch-option, and admin endpoints require an active
authenticated user. Disabled users receive `403`; invalid, expired, or deleted
user sessions receive `401`.

## Role Details

### Admin

Application behavior:

- Can view and operate on every instance returned by the selected backend.
- Can view metrics and costs across the selected backend scope.
- Can call every `/api/admin/users` endpoint.
- Cannot disable or delete their own account through the admin API.

Final UI behavior:

- IAM panel shows the user table.
- Can create users with any of the three roles.
- Can delete other users.
- Role/status update is supported by the backend API but is not exposed by the
  current IAM panel.

### DevOps Engineer

Application behavior:

- Can view and operate on every instance returned by the selected backend.
- Can launch and terminate instances.
- Can view metrics and costs across the selected backend scope.
- Cannot call `/api/admin/users`.

Final UI behavior:

- Can use the same instance, details, and monitoring controls as Admin.
- IAM user management is hidden.
- Advanced settings controls are presentation-only and are not persisted.

### User

Application behavior:

- Can launch instances.
- Can list, view, start, stop, reboot, terminate, and monitor only owned
  instances.
- Receives owned/scoped cost data.
- Cannot call `/api/admin/users`.

Ownership enforcement:

- Live mode tags launched instances and volumes with `CreatedBy=<user_id>`,
  `CreatedByEmail=<email>`, and `ManagedBy=CloudSim`.
- Mock mode stores ownership in `instances.created_by_user_id` and exposes it
  through the same `CreatedBy` tag contract.
- List, detail, lifecycle, and metric routes enforce ownership in FastAPI.
- Mock costs are calculated from visible owned mock instances.
- Live Cost Explorer requests use a `CreatedBy` tag filter for `User` accounts.
  The AWS cost allocation tag must be available for that filter to return data.

## Admin Account Paths

### Public registration

`POST /api/auth/register` is enabled in the final app and always creates an
active `User` account. It cannot create Admin or DevOps Engineer accounts.

### Admin-created users

An Admin can create a user with any valid role through:

```text
POST /api/admin/users
```

### Production bootstrap

The backend can create or restore the first production admin during startup:

```text
CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true
CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL=<admin-email>
CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD=<strong-secret-password>
CLOUDSIM_BOOTSTRAP_ADMIN_RESET_PASSWORD=false
```

Bootstrap settings belong on the backend only. Existing passwords are preserved
unless reset is explicitly enabled.

## Optional Live AWS Role Mapping

Role mapping is used only when both conditions are true:

```text
CLOUDSIM_AWS_BACKEND=live
ENABLE_ROLE_BASED_ACCESS=true
```

| CloudSim Role | Backend Setting | Typical IAM Role |
| :--- | :--- | :--- |
| Admin | `AWS_ROLE_ADMIN` | `CloudSimAdminRole` |
| DevOps Engineer | `AWS_ROLE_DEVOPS` | `CloudSimDevOpsRole` |
| User | `AWS_ROLE_READONLY` | `CloudSimUserRole` |

The backend calls STS AssumeRole and caches clients by user, role ARN, and AWS
service. Cost Explorer clients are created in `us-east-1`; EC2 and CloudWatch
clients use `AWS_REGION`.

When `ENABLE_ROLE_BASED_ACCESS=false`, live mode uses the backend service's
shared boto3 credential chain. FastAPI role and ownership checks still apply.

### Live IAM policy requirements

IAM policies must support the routes each CloudSim role is expected to use.
For example, because the application lets all authenticated roles launch
instances, a mapped `User` IAM role must allow the required EC2 launch, tag,
image, VPC, subnet, security-group, and volume describe actions if that behavior
should work in live role-based mode.

Use [setup-guides/IAM_Setup_Guide.md](setup-guides/IAM_Setup_Guide.md) as a
starting point, then validate its policies against this application matrix
before enabling live role-based production access.

## API Enforcement Reference

| API Group | Enforcement |
| :--- | :--- |
| `/api/auth/register` | Public; creates `User` role |
| `/api/auth/login` | Public credential check; rejects disabled accounts |
| `/api/auth/me` | Any active authenticated user |
| `/api/admin/users*` | `require_admin()` dependency |
| `/api/ec2/instances*` | Active user plus role/ownership checks |
| `/api/ec2/launch-options` | Any active authenticated user |
| `/api/ec2/instances/{id}/metrics*` | Active user plus ownership check |
| `/api/ec2/costs/*` | Any active authenticated user; service layer scopes `User` costs |

## Role Verification

Create a standard account through registration, then use an Admin to create a
DevOps Engineer account. Verify:

1. Admin sees all instances and the IAM user-management table.
2. DevOps Engineer sees all instances but no user-management table.
3. User sees only instances tagged/stored with their user ID.
4. Direct API requests from User to another user's detail, lifecycle, or metric
   endpoint receive `403`.
5. Direct non-Admin requests to `/api/admin/users` receive `403`.

## See Also

- [Architecture_Diagram.md](Architecture_Diagram.md)
- [WALKTHROUGH_GUIDELINE.md](WALKTHROUGH_GUIDELINE.md)
- [setup-guides/IAM_Setup_Guide.md](setup-guides/IAM_Setup_Guide.md)
- [deployment/PRODUCTION_DEPLOYMENT.md](deployment/PRODUCTION_DEPLOYMENT.md)
