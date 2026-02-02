// =============================================================================
// IAMPanel.tsx
// =============================================================================
// Identity and Access Management panel for managing users, roles, permissions,
// and advanced settings. Implements role-based access control (RBAC).
//
// ROLES:
// - Admin: Full access (user management CRUD, all EC2 operations, all settings)
// - DevOps Engineer: Full EC2 operations (including terminate), NO user management
// - User: Access only to their own instances (via CreatedBy tag)
//
// API CALLS:
// - adminApi.listUsers()   -> GET /api/admin/users
// - adminApi.createUser()  -> POST /api/admin/users
// - adminApi.deleteUser()  -> DELETE /api/admin/users/:id
//
// COMPONENT STRUCTURE:
// └── IAMPanel (Sheet)
//     ├── Header (Title, description)
//     ├── Overview Tab
//     │   ├── Current User Info Card
//     │   ├── User Management Section (Admin only)
//     │   │   ├── Users Table (list, delete)
//     │   │   └── Add User Dialog
//     │   ├── Role Permissions Reference
//     │   └── Audit Logs (mock)
//     ├── Advanced Settings Tab
//     │   ├── Instance Quotas
//     │   ├── Auto Scaling Policies
//     │   └── Notification Settings
//     └── Access Denied Dialog
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './ui/sheet';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Slider } from './ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { UserCircle, Shield, Settings, FileText, Bell, AlertTriangle, Users, Plus, Trash2, Loader2 } from 'lucide-react';
import { useUser, type UserRole } from '../contexts/UserContext';
import * as adminApi from '../api/admin';


// =============================================================================
// TYPES
// =============================================================================

interface IAMPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}


// =============================================================================
// CONSTANTS - Mock Data
// =============================================================================

// Mock audit logs
const auditLogs = [
  { id: 1, user: 'john.doe', action: 'Created instance i-1a2b3c4d', timestamp: '2025-11-14 10:30:15' },
  { id: 2, user: 'jane.smith', action: 'Modified auto-scale policy', timestamp: '2025-11-14 09:15:22' },
  { id: 3, user: 'admin.user', action: 'Added new user', timestamp: '2025-11-14 08:45:10' },
];


// =============================================================================
// COMPONENT
// =============================================================================

export function IAMPanel({ open, onOpenChange }: IAMPanelProps) {
  // ---------------------------------------------------------------------------
  // Context & State
  // ---------------------------------------------------------------------------
  const { user, hasRole } = useUser();

  // Access denied dialog state
  const [showAccessDenied, setShowAccessDenied] = useState(false);
  const [deniedAction, setDeniedAction] = useState('');
  const [deniedRequiredRole, setDeniedRequiredRole] = useState<UserRole>(null);

  // User management state
  const [users, setUsers] = useState<adminApi.AdminUser[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [showAddUserDialog, setShowAddUserDialog] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState('User');
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [userError, setUserError] = useState('');

  // ---------------------------------------------------------------------------
  // API Handlers - Fetch Users
  // ---------------------------------------------------------------------------

  // Fetch users when panel opens (Admin only)
  useEffect(() => {
    if (open && user?.role === 'Admin') {
      fetchUsers();
    }
  }, [open, user?.role]);

  const fetchUsers = async () => {
    setIsLoadingUsers(true);
    try {
      // API CALL: GET /api/admin/users
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    } finally {
      setIsLoadingUsers(false);
    }
  };

  // ---------------------------------------------------------------------------
  // API Handlers - Create User
  // ---------------------------------------------------------------------------

  const handleCreateUser = async () => {
    setUserError('');
    setIsCreatingUser(true);
    try {
      // API CALL: POST /api/admin/users
      await adminApi.createUser({
        email: newUserEmail,
        password: newUserPassword,
        role: newUserRole,
      });
      setShowAddUserDialog(false);
      setNewUserEmail('');
      setNewUserPassword('');
      setNewUserRole('User');
      fetchUsers();
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Failed to create user';
      setUserError(message);
    } finally {
      setIsCreatingUser(false);
    }
  };

  // ---------------------------------------------------------------------------
  // API Handlers - Delete User
  // ---------------------------------------------------------------------------

  const handleDeleteUser = async (userId: number, email: string) => {
    if (!confirm(`Are you sure you want to delete ${email}?`)) return;
    try {
      // API CALL: DELETE /api/admin/users/:id
      await adminApi.deleteUser(userId);
      fetchUsers();
    } catch (err) {
      console.error('Failed to delete user:', err);
    }
  };

  // ---------------------------------------------------------------------------
  // Helpers - Access Control
  // ---------------------------------------------------------------------------

  const checkAccess = (requiredRole: UserRole, action: string) => {
    if (!hasRole(requiredRole)) {
      setDeniedAction(action);
      setDeniedRequiredRole(requiredRole);
      setShowAccessDenied(true);
      return false;
    }
    return true;
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="sm:max-w-2xl w-full overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              IAM & Settings
            </SheetTitle>
            <SheetDescription>
              Manage identity, access control, and advanced settings
            </SheetDescription>
          </SheetHeader>

          <Tabs defaultValue="overview" className="mt-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="advanced">Advanced Settings</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="mt-4 space-y-6">
              {/* Current User Info */}
              <Card className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  <UserCircle className="h-5 w-5 text-blue-600" />
                  <h3 className="font-medium">Current User</h3>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Email</span>
                    <span className="text-sm">{user?.email}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Role</span>
                    <Badge variant="outline">{user?.role}</Badge>
                  </div>
                </div>
              </Card>

              {/* User Management (Admin Only) */}
              {user?.role === 'Admin' && (
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Users className="h-5 w-5 text-green-600" />
                      <h3 className="font-medium">User Management</h3>
                    </div>
                    <Button size="sm" onClick={() => setShowAddUserDialog(true)}>
                      <Plus className="h-4 w-4 mr-1" /> Add User
                    </Button>
                  </div>

                  {isLoadingUsers ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-5 w-5 animate-spin text-gray-500" />
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Email</TableHead>
                          <TableHead>Role</TableHead>
                          <TableHead></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {users.map((u) => (
                          <TableRow key={u.id}>
                            <TableCell className="text-sm">{u.email}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{u.role}</Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              {u.email !== user?.email && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteUser(u.id, u.email)}
                                >
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </Card>
              )}

              {/* Role Permissions Reference */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="h-5 w-5 text-purple-600" />
                  <h3 className="font-medium">Role Permissions</h3>
                </div>

                <div className="space-y-3">
                  {/* Admin */}
                  <div className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">Admin</span>
                      <Badge className="bg-red-600">Full Access</Badge>
                    </div>
                    <p className="text-xs text-gray-600">
                      Full access to all resources, user management, and settings
                    </p>
                  </div>

                  {/* DevOps Engineer */}
                  <div className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">DevOps Engineer</span>
                      <Badge className="bg-orange-600">Read/Write</Badge>
                    </div>
                    <p className="text-xs text-gray-600">
                      Manage instances, view monitoring, configure auto-scaling
                    </p>
                  </div>

                  {/* User */}
                  <div className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">User</span>
                      <Badge className="bg-blue-600">Read Only</Badge>
                    </div>
                    <p className="text-xs text-gray-600">
                      View instances and monitoring data only
                    </p>
                  </div>
                </div>
              </Card>

              {/* Audit Logs */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="h-5 w-5 text-gray-600" />
                  <h3 className="font-medium">Recent Audit Logs</h3>
                  <Badge variant="outline" className="ml-auto">Mock Data</Badge>
                </div>

                <div className="space-y-2">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="flex justify-between p-2 text-sm bg-gray-50 rounded">
                      <div>
                        <span className="font-medium">{log.user}</span>
                        <span className="text-gray-600 ml-2">{log.action}</span>
                      </div>
                      <span className="text-gray-500 text-xs">{log.timestamp}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </TabsContent>

            {/* Advanced Settings Tab */}
            <TabsContent value="advanced" className="mt-4 space-y-6">
              {/* Instance Quotas */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Settings className="h-5 w-5 text-blue-600" />
                  <h3 className="font-medium">Resource Quotas</h3>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label>Max Instances</Label>
                      <span className="text-sm">20</span>
                    </div>
                    <Slider defaultValue={[20]} max={50} step={1} disabled={!hasRole('Admin')} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label>Max vCPUs</Label>
                      <span className="text-sm">40</span>
                    </div>
                    <Slider defaultValue={[40]} max={100} step={1} disabled={!hasRole('Admin')} />
                  </div>
                </div>

                {!hasRole('Admin') && (
                  <p className="text-xs text-gray-500 mt-3">Admin role required to modify quotas</p>
                )}
              </Card>

              {/* Auto Scaling Policies */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Settings className="h-5 w-5 text-green-600" />
                  <h3 className="font-medium">Auto Scaling Policies</h3>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Enable Auto Scaling</Label>
                      <p className="text-xs text-gray-600">Automatically scale based on demand</p>
                    </div>
                    <Switch
                      defaultChecked
                      disabled={!hasRole('DevOps Engineer')}
                      onCheckedChange={() => {
                        if (!hasRole('DevOps Engineer')) {
                          checkAccess('DevOps Engineer', 'enable auto scaling');
                        }
                      }}
                    />
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <Label>Scale Up Threshold (CPU %)</Label>
                    <Input
                      type="number"
                      defaultValue="80"
                      disabled={!hasRole('DevOps Engineer')}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Scale Down Threshold (CPU %)</Label>
                    <Input
                      type="number"
                      defaultValue="20"
                      disabled={!hasRole('DevOps Engineer')}
                    />
                  </div>
                </div>
              </Card>

              {/* Notification Settings */}
              <Card className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Bell className="h-5 w-5 text-orange-600" />
                  <h3 className="font-medium">Notifications</h3>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Email Alerts</Label>
                      <p className="text-xs text-gray-600">Receive alerts via email</p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Slack Integration</Label>
                      <p className="text-xs text-gray-600">Send alerts to Slack channel</p>
                    </div>
                    <Switch disabled={!hasRole('DevOps Engineer')} />
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <Label>Alert Email</Label>
                    <Input
                      type="email"
                      placeholder="alerts@company.com"
                      disabled={!hasRole('DevOps Engineer')}
                    />
                  </div>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </SheetContent>
      </Sheet>

      {/* Add User Dialog */}
      <Dialog open={showAddUserDialog} onOpenChange={setShowAddUserDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
            <DialogDescription>
              Create a new user account with the specified role
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            {userError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{userError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="new-email">Email</Label>
              <Input
                id="new-email"
                type="email"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
                placeholder="user@example.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-password">Password</Label>
              <Input
                id="new-password"
                type="password"
                value={newUserPassword}
                onChange={(e) => setNewUserPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-role">Role</Label>
              <Select value={newUserRole} onValueChange={setNewUserRole}>
                <SelectTrigger id="new-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Admin">Admin</SelectItem>
                  <SelectItem value="DevOps Engineer">DevOps Engineer</SelectItem>
                  <SelectItem value="User">User</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowAddUserDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateUser} disabled={isCreatingUser || !newUserEmail || !newUserPassword}>
              {isCreatingUser && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Access Denied Dialog */}
      <Dialog open={showAccessDenied} onOpenChange={setShowAccessDenied}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Access Denied
            </DialogTitle>
            <DialogDescription>
              You do not have permission to {deniedAction}
            </DialogDescription>
          </DialogHeader>

          <Alert variant="destructive" className="mt-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Insufficient Permissions</AlertTitle>
            <AlertDescription>
              This action requires the <strong>{deniedRequiredRole}</strong> role or higher.
              Your current role is <strong>{user?.role}</strong>.
            </AlertDescription>
          </Alert>

          <DialogFooter className="mt-4">
            <Button onClick={() => setShowAccessDenied(false)}>
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
