# CloudSim User Journey - Admin Role

> **Role:** Admin  
> **IAM Role:** `CloudSimAdminRole`  
> **IAM Policy:** `CloudSimAdminPolicy`  
> **Access Level:** Full Access — every feature available to DevOps plus user CRUD (`/api/admin/users`) and modifiable resource quotas.  
> **Admin Source:** Backend bootstrap or Admin-created account
> **Last Updated:** May 2026

## Persona

**Jordan** — CTO and co-founder of a small startup.

## Scenario

Jordan is the technical co-founder of a startup that uses CloudSim to manage the team's AWS EC2 infrastructure. As the only Admin, Jordan is responsible for onboarding new team members, assigning roles (User, DevOps Engineer, or Admin), and ensuring the cloud environment stays healthy and cost-effective. Jordan provisions instances for developers, monitors resource usage across all users, terminates instances that are no longer needed, and configures system-wide settings like auto-scaling thresholds and resource quotas. Unlike other roles, Jordan has full cross-user visibility - every instance, every alarm, every metric is accessible regardless of who created it.

## Goals

- **Manage the team**: add new users, assign appropriate roles, and remove accounts when people leave
- **Maintain full visibility**: see all instances across all users to catch orphaned resources or unexpected activity
- **Control infrastructure costs**: terminate idle instances, configure auto-scaling policies, and monitor Cost Explorer data
- **Configure system-wide settings**: adjust resource quotas, notification preferences, and scaling thresholds

## Journey Stages

| Stage | Description |
|-------|-------------|
| **Authentication** | Admin logs in and receives full-access JWT token |
| **Dashboard - Cross-User Visibility** | Admin sees all instances across all users in a single view |
| **User Management** | Admin adds, removes, and assigns roles to team members |
| **Instance Termination** | Admin terminates instances from any user |
| **Monitoring All Instances** | Admin reviews CloudWatch metrics for any instance across the platform |
| **Advanced Settings** | Admin configures resource quotas, auto-scaling, and notifications |

## Stage 1 - Authentication

Jordan navigates to `localhost:5173` and enters the configured admin credentials into the CloudSim login modal. After clicking Sign In, the backend authenticates the request and returns a JWT token containing the `Admin` role. Jordan is redirected to the Dashboard with an `Admin` badge displayed next to the email in the top navigation bar. The login flow is identical across all roles - the difference is in what the token unlocks.

## Stage 2 - Dashboard & Cross-User Visibility

Unlike the User role (which sees only own instances), Jordan's dashboard shows all instances across all users. The All Instances table lists instances from every user, including `web-server-01` (created by `user@gmail.com`) and `web-server-02` (created by `user2@gmail.com`), each with full action buttons for Stop, Reboot, and Terminate.

![Admin Dashboard](../images/admin/01-dashboard-all-instances.png)
*Admin dashboard showing all instances across all users with full action controls.*

The lower section includes an Instance Alarms panel with alarm statuses across all instances (`web-server-01-cpu-high` OK, `db-server-01-disk` ALARM), an Availability Zone Health panel showing instance distribution and average CPU per zone, and the Resource Usage Summary.

## Stage 3 - User Management

Jordan clicks **IAM & Settings** in the top navigation to open the settings sidebar. The Overview tab is significantly different from the User and DevOps views because it includes the **User Management** section - an Admin-exclusive feature. This section shows a table of all registered accounts with their email, role, and a delete action button.

![IAM & Settings - Admin Overview](../images/admin/02-iam-user-management.png)
*Admin Overview tab with User Management section showing all registered accounts.*

Below the user table, the Role Permissions panel shows all three role levels (Admin - Full Access; DevOps Engineer - Read/Write; User - Read Only), and Recent Audit Logs display mock entries for recent actions.

## Stage 4 - Add New User

From the User Management section, Jordan clicks **+ Add User** to open the user creation modal. The modal provides fields for Email, Password, and a Role dropdown with options for Admin, DevOps Engineer, or User. Jordan fills in the details for a new DevOps Engineer (`deng2@gmail.com`) and clicks **Create User** (which calls `POST /api/admin/users`, hashed via bcrypt server-side).

![Add New User Modal](../images/admin/03-add-new-user-modal.png)
*Add New User modal with email, password, and role selection.*

After creation, the User Management table immediately updates to show the new account.

![User Created - Updated List](../images/admin/04-user-created-success.png)
*User Management table now showing 5 users including the newly created `deng2@gmail.com`.*

## Stage 5 - Instance Termination

Jordan has the ability to terminate any instance across all users. This is done by clicking the trash icon (🗑) in the Actions column of the instance table. After clicking terminate on both instances, their state transitions to **shutting-down** (orange badge). The Running count drops to 0 while Total Instances still shows 2 during the shutdown process.

![Instances Shutting Down](../images/admin/05-instances-shutting-down.png)
*Both instances showing "shutting-down" state after Admin-initiated termination.*

## Stage 6 - Monitoring All Instances

Jordan navigates to the **Monitoring** tab to view performance metrics for any instance. The instance selector dropdown lists all instances across all users. Jordan selects `web-server-02` and reviews the metric summary cards: CPU Utilization (4.7%), Memory Usage (512 MB), Network In (420 B), Disk Ops (0/s), and Today's Cost ($3.80).

![Admin Monitoring - CPU](../images/admin/06-monitoring-cpu-chart.png)
*CPU Utilization chart showing real CloudWatch data rising from ~0% to ~4% over 5 minutes.*

The monitoring view provides the same five tabs as other roles (CPU, Memory, Network, Disk I/O, Cost), but with access to any instance and the full Cost Explorer dataset. Each CloudWatch fetch is persisted to the local `metrics` table for historical analysis. System Logs are displayed below the charts.

## Stage 7 - Advanced Settings

Jordan has full modification rights on all advanced settings. The **Resource Quotas** section allows adjusting Max Instances and Max vCPUs - other roles see these as view-only with a warning. **Auto Scaling Policies** can be toggled on/off with configurable Scale Up and Scale Down thresholds. **Notifications** allow toggling Email Alerts and Slack Integration, and setting the alert email address.

| Setting | Admin Access |
|---------|-------------|
| Resource Quotas (Max Instances, Max vCPUs) | ✅ Can modify |
| Auto Scaling Policies | ✅ Can toggle and configure |
| Notifications (Email, Slack, Alert Email) | ✅ Can modify |

## Permissions Summary

### Allowed Actions (Full Access)

```text
ec2:*                          (all EC2 actions)
cloudwatch:*                   (all CloudWatch actions)
ce:GetCostAndUsage             (Cost Explorer)
ce:GetCostForecast             (Cost Forecasting)
/api/admin/users (GET, POST, PUT, DELETE)   (CloudSim user CRUD)
```

### Explicitly Denied

```text
(none — Admin has unrestricted access in CloudSim)
```

### Self-Protection Rules

Even with full access, Admins cannot:

- **Disable their own account** — `PUT /api/admin/users/{self_id}` with `is_active=false` returns 400.
- **Delete their own account** — `DELETE /api/admin/users/{self_id}` returns 400.

These guardrails prevent the last Admin from accidentally locking themselves out.

## Admin vs Other Roles

| Feature | Admin | DevOps Engineer | User |
|---------|-------|-----------------|------|
| View all instances (cross-user) | ✅ | ✅ | ❌ (own only) |
| Launch instances | ✅ | ✅ | ✅ |
| Start / Stop | ✅ | ✅ (any) | ✅ (own only) |
| Reboot | ✅ | ✅ | ✅ (own only) |
| Terminate instances | ✅ | ✅ | ✅ (own only) |
| User management | ✅ | ❌ | ❌ |
| Modify resource quotas | ✅ | ❌ | ❌ |
| Configure auto-scaling | ✅ | ✅ | ❌ |
| View CloudWatch metrics | ✅ | ✅ | ✅ (own only) |
| Access Cost Explorer | ✅ | ✅ | ❌ |
| CloudWatch alarms | ✅ | ✅ | ✅ (own only) |

## Navigation Map

```text
Login Page
  └── Dashboard (full cross-user visibility)
        ├── Account Overview (cards - all users' instances counted)
        ├── All Instances (table - shows ALL users' instances)
        │     ├── Stop / Reboot / Terminate actions on ANY instance
        │     └── Click instance name → Instance Details
        │           ├── Details tab
        │           ├── Security tab
        │           ├── Networking tab
        │           ├── Storage tab
        │           └── Tags tab
        ├── Instance Alarms (panel - all alarms)
        ├── Availability Zone Health (panel)
        └── Resource Usage Summary (panel)
  └── Instance Details (tab)
  └── Monitoring (tab - can monitor ANY instance)
        ├── CPU chart (CloudWatch data)
        ├── Memory chart
        ├── Network chart
        ├── Disk I/O chart
        ├── Cost chart
        └── System Logs
  └── IAM & Settings (sidebar)
        ├── Overview tab
        │     ├── Current User (Admin)
        │     ├── ★ User Management (Admin-only)
        │     │     ├── View all users
        │     │     ├── + Add User (with role assignment)
        │     │     └── Delete users
        │     ├── Role Permissions
        │     └── Recent Audit Logs
        └── Advanced Settings tab
              ├── Resource Quotas (editable)
              ├── Auto Scaling Policies (editable)
              └── Notifications (editable)
  └── + Launch Instance (wizard)
        ├── Step 1: Name & AMI
        ├── Step 2: Instance Type
        ├── Step 3: Network & Storage
        └── Step 4: Review & Launch
  └── Logout
```
