// Describe groups related test; each 'it' block is an individual test case; vi is mocking tool; expect is assertion.
import { describe, expect, it, vi } from 'vitest';

// Import shared Axios client instance for mocking API calls.
import { api } from './client'; 

// Imports auth functions and types to be tested.
import {
  getStoredUser,
  getToken,
  isAuthenticated,
  login,
  logout,
  removeToken,
  setStoredUser,
  setToken,
  type User,
} from './auth'; 


describe('auth token storage', () => {
  // Tests for auth token storage and retrieval functions.
  it('stores and clears token data', () => {
    setToken('test-token');

    expect(getToken()).toBe('test-token');
    expect(isAuthenticated()).toBe(true);

    removeToken();

    expect(getToken()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  // Tests for user data storage and retrieval functions.
  it('stores and reads the cached user', () => {
    const user: User = {
      id: 1,
      email: 'admin-test@example.com',
      role: 'Admin',
      is_active: true,
    };

    setStoredUser(user);

    expect(getStoredUser()).toEqual(user);
  });
});

// Tests for the login and logout functions, which involve API calls and state management.
describe('auth api', () => {
  // Spy is used to mock the API call made by the login function, allowing us to test the function's behavior without making real HTTP requests.
  it('posts login as OAuth form data and stores returned token', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValueOnce({
      data: {
        access_token: 'jwt-token',
        token_type: 'bearer',
      },
    });

    // Call the real login function with test credentials and capture the API call made by it.
    const response = await login('admin-test@example.com', 'testpassword123');
    const submittedBody = postSpy.mock.calls[0]?.[1];

    // Assert that the API call was made with the correct URL, form data, and headers, and that the response is handled correctly by the login function.
    expect(postSpy).toHaveBeenCalledWith(
      '/api/auth/login',
      expect.any(URLSearchParams),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      },
    );
    // The form data is sent as URLSearchParams, so we convert it to a string for comparison. %40 is the URL-encoded form of '@'
    expect(submittedBody?.toString()).toBe(
      'username=admin-test%40example.com&password=testpassword123',
    );
    expect(response.access_token).toBe('jwt-token');
    expect(getToken()).toBe('jwt-token');

    // Restore the original API post method after the test to avoid affecting other tests.
    postSpy.mockRestore();
  });

  // Tests that the logout function correctly clears all stored authentication state, including the token and user data.
  it('logout clears all stored auth state', () => {
    setToken('jwt-token');
    setStoredUser({
      id: 2,
      email: 'devops-test@example.com',
      role: 'DevOps Engineer',
      is_active: true,
    });

    logout();

    expect(getToken()).toBeNull();
    expect(getStoredUser()).toBeNull();
  });
});
