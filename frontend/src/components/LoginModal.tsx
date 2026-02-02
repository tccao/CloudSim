// =============================================================================
// LoginModal.tsx
// =============================================================================
// Authentication modal for user login and registration. Provides a login form
// that authenticates users via JWT tokens from the backend auth API.
//
// API CALLS:
// - UserContext.loginWithCredentials() -> POST /api/auth/login
// - UserContext.register() -> POST /api/auth/register
//
// COMPONENT STRUCTURE:
// └── LoginModal
//     ├── Header (Logo + Title)
//     ├── Error Alert (conditional)
//     ├── Email Input
//     ├── Password Input
//     ├── Submit Button (Login/Register)
//     └── Mode Toggle Button
// =============================================================================


// =============================================================================
// IMPORTS
// =============================================================================

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useUser } from '../contexts/UserContext';
import { AlertCircle, Loader2, Cloud } from 'lucide-react';


// =============================================================================
// TYPES
// =============================================================================

interface LoginModalProps {
  open: boolean;
}


// =============================================================================
// COMPONENT
// =============================================================================

export function LoginModal({ open }: LoginModalProps) {
  // ---------------------------------------------------------------------------
  // Context & State
  // ---------------------------------------------------------------------------
  const { loginWithCredentials, register, error, clearError, isLoading } = useUser();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [localError, setLocalError] = useState('');

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  // Handle login/registration with real backend
  // Uses JWT auth via the auth API
  const handleSubmit = async () => {
    setLocalError('');
    clearError();

    if (!email || !password) {
      setLocalError('Please enter both email and password');
      return;
    }

    try {
      if (isRegisterMode) {
        await register(email, password);
      } else {
        await loginWithCredentials(email, password);
      }
      // Success - context will update user state
    } catch (err) {
      setLocalError((err as Error).message);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && email && password) {
      handleSubmit();
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={() => { }}>
      <DialogContent className="max-w-md">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl shadow-lg">
              <Cloud className="h-8 w-8 text-white" />
            </div>
          </div>
          <DialogTitle className="text-2xl">Welcome to CloudSim</DialogTitle>
          <DialogDescription>
            {isRegisterMode
              ? 'Create an account to get started'
              : 'Sign in to manage your cloud infrastructure'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Error Alert */}
          {(localError || error) && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{localError || error}</AlertDescription>
            </Alert>
          )}

          {/* Email Input */}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setLocalError('');
              }}
              onKeyDown={handleKeyDown}
              autoComplete="email"
            />
          </div>

          {/* Password Input */}
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setLocalError('');
              }}
              onKeyDown={handleKeyDown}
              autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
            />
          </div>

          {/* Submit Button */}
          <Button
            className="w-full bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
            onClick={handleSubmit}
            disabled={!email || !password || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {isRegisterMode ? 'Creating Account...' : 'Signing in...'}
              </>
            ) : (
              isRegisterMode ? 'Create Account' : 'Sign In'
            )}
          </Button>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">
                {isRegisterMode ? 'Already have an account?' : 'New to CloudSim?'}
              </span>
            </div>
          </div>

          {/* Mode Toggle Button */}
          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              setIsRegisterMode(!isRegisterMode);
              setLocalError('');
              clearError();
            }}
          >
            {isRegisterMode ? 'Sign In Instead' : 'Create Account'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
