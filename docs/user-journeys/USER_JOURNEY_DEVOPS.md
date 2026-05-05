# CloudSim User Journey - DevOps Engineer Role

> **Role:** DevOps Engineer  
> **IAM Role:** `CloudSimDevOpsRole`  
> **IAM Policy:** `CloudSimDevOpsPolicy`  
> **Access Level:** Read/Write — Full EC2 lifecycle on any instance, CloudWatch, Cost Explorer, auto-scaling and notifications config. View-only resource quotas. No user management.  
> **Test Account:** `deng@gmail.com`  
> **Last Updated:** May 2026

## Persona

**Sam** — DevOps Engineer responsible for provisioning and maintaining the team's cloud infrastructure.

## Scenario

Sam is the DevOps Engineer at a small startup that uses CloudSim to manage AWS EC2 instances. Sam's primary job is to provide extra help for developers, keep their cloud instances running smoothly, and make sure the team isn't burning through the cloud budget. Sam has cross-user visibility into all instances - not just his own - so he can spot idle resources, investigate alarm states, and terminate instances that are no longer needed. He also configures auto-scaling policies and notification alerts. The two things Sam cannot do are manage user accounts (that's the Admin's job) and modify resource quotas. Sam logs in daily to check the dashboard, launch new instances when the team needs them, and review CloudWatch metrics and Cost Explorer data.

## Goals

- **Monitor everything**: review CloudWatch metrics, alarms, and Cost Explorer data across all users' instances
- **Keep costs under control**: identify idle or oversized instances and terminate or resize them
- **Configure operational policies**: set auto-scaling thresholds and notification alerts without needing Admin intervention

## Journey Stages

| Stage | Description |
|-------|-------------|
| **Authentication** | DevOps Engineer logs in and receives read/write JWT token |
| **Dashboard - Cross-User Visibility** | DevOps Engineer sees all instances across all users |
| **Instance Management** | DevOps Engineer launches, stops, reboots, and terminates instances for any user |
| **Monitoring & CloudWatch** | DevOps Engineer reviews metrics, cost data, and system logs for any instance |
| **Settings - Overview** | DevOps Engineer views role info and audit logs (no user management) |
| **Settings - Advanced** | DevOps Engineer configures auto-scaling and notifications (quotas are read-only) |
| **Restrictions** | DevOps Engineer encounters permission boundaries for user management and quotas |

## Stage 1 - Authentication

Sam navigates to `localhost:5173` and enters credentials (`deng@gmail.com`) into the CloudSim login modal. After clicking Sign In, the backend authenticates the request and returns a JWT token containing the `DevOps Engineer` role. Sam is redirected to the Dashboard with a `DevOps Engineer` badge displayed next to the email in the top navigation bar.

![DevOps Login](../images/deng/01-login-credentials.png)
*Credentials filled in for the DevOps Engineer test account.*

## Stage 2 - Dashboard & Cross-User Visibility

Like the Admin, Sam's dashboard shows all instances across all users - not just his own. The All Instances table lists instances from every user, including `web-server-01` (created by `user@gmail.com`) and `web-server-02` (created by `user2@gmail.com`), each with full action buttons for Stop, Reboot, and Terminate.

![DevOps Dashboard](../images/deng/02-dashboard-all-instances.png)
*DevOps Engineer dashboard showing all instances across all users with full action controls.*

The lower section includes an Instance Alarms panel with alarm statuses across all instances (`web-server-01-cpu-high` OK, `db-server-01-disk` ALARM), and an Availability Zone Health panel showing instance distribution and average CPU per zone.

## Stage 3 - Instance Management

Sam can launch new EC2 instances using the same 4-step wizard available to all roles. Step 1 configures the instance name and AMI selection. Step 2 selects the instance type. Step 3 handles network and storage. Step 4 presents a full review with estimated monthly cost before launching.

Beyond launching, Sam can perform lifecycle actions on any instance across all users - not just his own. Stop, Reboot, Start, and Terminate are all available through the action buttons in the instance table or the Instance Details page.

## Stage 4 - Monitoring & CloudWatch

Sam navigates to the **Monitoring** tab to review performance metrics. The instance selector dropdown lists all instances across all users. Sam can select any instance and review metric summary cards for CPU Utilization, Memory Usage, Network In, Disk Ops, and Today's Cost.

The monitoring view provides five tabs — **CPU**, **Memory**, **Network**, **Disk I/O**, and **Cost** — each rendering a time-series chart for the selected instance and time range. Each CloudWatch fetch is also persisted to the local `metrics` table, building a historical dataset Sam can later use for trend analysis. Below the charts, a System Logs section displays timestamped log entries with INFO/WARN level tags. Sam has full Cost Explorer access for tracking spending trends across the team.

![DevOps Monitoring](../images/deng/03-monitoring.png)
*DevOps Engineer monitoring view showing CPU metrics for a selected instance.*

## Stage 5 - Settings - Overview

Sam clicks **IAM & Settings** in the top navigation to open the settings sidebar. The Overview tab shows his email and role, a Role Permissions panel with all three role levels (Admin - Full Access; DevOps Engineer - Read/Write; User - Read Only), and Recent Audit Logs. Unlike the Admin view, there is no User Management section - Sam cannot add, delete, or modify user accounts.

![IAM & Settings - DevOps Overview](../images/deng/04-iam-settings-overview.png)
*DevOps Engineer Overview tab - no User Management section visible.*

## Stage 6 - Settings - Advanced

Sam switches to the **Advanced Settings** tab. Resource Quotas (Max Instances: 20, Max vCPUs: 40) are displayed as view-only with a warning that modification requires Admin access. However, Sam can configure **Auto Scaling Policies** - toggling auto-scaling on/off and adjusting Scale Up and Scale Down thresholds. Notifications for Email Alerts and Slack Integration are also configurable.

![IAM & Settings - DevOps Advanced](../images/deng/05-iam-settings-advanced.png)
*Advanced Settings tab showing view-only quotas but editable auto-scaling and notifications.*

| Setting | DevOps Access |
|---------|--------------|
| Resource Quotas (Max Instances, Max vCPUs) | 👁 View only |
| Auto Scaling Policies | ✅ Can toggle and configure |
| Notifications (Email, Slack, Alert Email) | ✅ Can modify |

## Stage 7 - Restrictions

Sam's role has two boundaries. First, the User Management section is completely hidden from the IAM & Settings view - Sam cannot view the user list, add new users, delete users, or modify roles. Second, Resource Quotas are displayed as view-only with sliders disabled. If Sam needs a quota change or a new user account, he must request it from Jordan (the Admin).

## Permissions Summary

### Allowed Actions
```
ec2:DescribeInstances
ec2:DescribeInstanceStatus
ec2:RunInstances
ec2:StartInstances
ec2:StopInstances
ec2:RebootInstances
ec2:CreateTags
ec2:DescribeSecurityGroups
ec2:DescribeSubnets
ec2:DescribeVpcs
ec2:DescribeImages
ec2:DescribeKeyPairs
ec2:DescribeVolumes
cloudwatch:GetMetricData
cloudwatch:GetMetricStatistics
cloudwatch:ListMetrics
cloudwatch:DescribeAlarms
cloudwatch:PutMetricAlarm
cloudwatch:DeleteAlarms
ce:GetCostAndUsage
ce:GetCostForecast
```

### Explicitly Denied
```
ec2:CreateVpc
ec2:DeleteVpc
ec2:ModifyVpc*
```

## DevOps vs Other Roles

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

```
Login Page
  └── Dashboard (cross-user visibility - sees all instances)
        ├── Account Overview (cards - all instances counted)
        ├── All Instances (table - shows ALL users' instances)
        │     ├── Stop / Reboot / Terminate actions on ANY instance
        │     └── Click instance name → Instance Details
        │           ├── Details tab
        │           ├── Security tab
        │           ├── Networking tab
        │           ├── Storage tab
        │           └── Tags tab
        ├── Instance Alarms (panel)
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
        │     ├── Current User (DevOps Engineer)
        │     ├── ✗ User Management (NOT available)
        │     ├── Role Permissions
        │     └── Recent Audit Logs
        └── Advanced Settings tab
              ├── Resource Quotas (view-only)
              ├── Auto Scaling Policies (editable)
              └── Notifications (editable)
  └── + Launch Instance (wizard)
        ├── Step 1: Name & AMI
        ├── Step 2: Instance Type
        ├── Step 3: Network & Storage
        └── Step 4: Review & Launch
  └── Logout
```
