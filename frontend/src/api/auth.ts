/**
 * =============================================================================
 * CloudSim Authentication API Client
 * =============================================================================
 * 
 * PURPOSE:
 * Handles user authentication, JWT token management, and session state.
 * 
 * ARCHITECTURE:
 *   Browser (this file)  →  Backend (FastAPI)  →  PostgreSQL (users table)
 *   login()              →  POST /api/auth/login →  verify password, return JWT
 * 
 * DESIGN DECISIONS:
 *   1. Token stored in localStorage - Simple but has XSS vulnerability trade-off
 *      - Alternative: httpOnly cookies (more secure but requires backend changes)
 *   2. Axios interceptors - Automatically attach token to all requests
 *   3. FormData for login - OAuth2 spec requires form-urlencoded, not JSON
 * 
 * =============================================================================
 */

import { api } from './client';


// =============================================================================
// SECTION 1: TYPE DEFINITIONS
// =============================================================================

/** CloudSim user returned by the backend */
export interface User {
    id: number;
    email: string;
    role: string;  // Admin, Developer, DevOps Engineer, User
    is_active: boolean;
}

/** JWT token response from login */
export interface LoginResponse {
    access_token: string;
    token_type: string;
}

/** Data required to register a new user */
export interface RegisterData {
    email: string;
    password: string;
}


// =============================================================================
// SECTION 2: TOKEN STORAGE
// =============================================================================
// Tokens are stored in localStorage. For production apps with higher security
// requirements, consider using httpOnly cookies instead.

const TOKEN_KEY = 'cloudsim_access_token';
const USER_KEY = 'cloudsim_user';


/**
 * Store JWT token in browser localStorage.
 * 
 * SECURITY NOTE:
 * localStorage is vulnerable to XSS attacks. If an attacker can inject
 * JavaScript, they can steal the token. For production, use httpOnly cookies.
 */
export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}


/** Retrieve stored JWT token */
export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}


/** Clear all authentication data */
export function removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}


/** Store user data for quick access without API call */
export function setStoredUser(user: User): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}


/** Get cached user data */
export function getStoredUser(): User | null {
    const data = localStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
}


// =============================================================================
// SECTION 3: AXIOS INTERCEPTORS
// =============================================================================
// Interceptors automatically modify requests/responses.
// This is how the JWT token gets attached to every API call.

/**
 * REQUEST INTERCEPTOR: Attach JWT token to all outgoing requests.
 * 
 * Before every HTTP request, this adds:
 *   Authorization: Bearer eyJhbGci...
 */
api.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});


/**
 * RESPONSE INTERCEPTOR: Handle 401 Unauthorized globally.
 * 
 * If any API call returns 401, the token is invalid/expired.
 * We clear the stored token so the user will be prompted to login.
 */
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            removeToken();
            // The UI should detect this and show login modal
        }
        return Promise.reject(error);
    }
);


// =============================================================================
// SECTION 4: AUTHENTICATION API FUNCTIONS
// =============================================================================

/**
 * Register a new user account.
 * 
 * CURL TEST:
 * ```bash
 * curl -X POST http://localhost:8000/api/auth/register \
 *   -H "Content-Type: application/json" \
 *   -d '{"email": "newuser@example.com", "password": "securepassword123"}'
 * ```
 * 
 * RESPONSE (201 Created):
 * ```json
 * {
 *   "id": 5,
 *   "email": "newuser@example.com",
 *   "role": "User",
 *   "is_active": true
 * }
 * ```
 * 
 * ERROR (409 Conflict): Email already exists
 */
export async function register(data: RegisterData): Promise<User> {
    const response = await api.post<User>('/api/auth/register', data);
    return response.data;
}


/**
 * Login with email and password.
 * 
 * IMPORTANT: OAuth2 requires form-urlencoded data, NOT JSON!
 * This is why we use URLSearchParams instead of a JSON body.
 * 
 * CURL TEST:
 * ```bash
 * # Form-urlencoded format (OAuth2 standard)
 * curl -X POST http://localhost:8000/api/auth/login \
 *   -H "Content-Type: application/x-www-form-urlencoded" \
 *   -d "username=admin@gmail.com&password=admin123"
 * ```
 * 
 * RESPONSE (200 OK):
 * ```json
 * {
 *   "access_token": "eyJhbGciOiJIUzI1NiIs...",
 *   "token_type": "bearer"
 * }
 * ```
 * 
 * TEST ACCOUNTS (from seed data):
 *   - admin@gmail.com / admin123 (Admin role)
 *   - dev@gmail.com / dev123 (Developer role)
 *   - deng@gmail.com / deng123 (DevOps Engineer role)
 *   - user@gmail.com / user123 (User role)
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
    // OAuth2 spec requires form data, not JSON
    const formData = new URLSearchParams();
    formData.append('username', email);  // OAuth2 uses "username" field
    formData.append('password', password);

    const response = await api.post<LoginResponse>('/api/auth/login', formData, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });

    // Store token immediately after successful login
    setToken(response.data.access_token);

    return response.data;
}


/**
 * Get current authenticated user's information.
 * 
 * CURL TEST:
 * ```bash
 * curl -X GET http://localhost:8000/api/auth/me \
 *   -H "Authorization: Bearer YOUR_JWT_TOKEN"
 * ```
 * 
 * RESPONSE:
 * ```json
 * {
 *   "id": 1,
 *   "email": "admin@gmail.com",
 *   "role": "Admin",
 *   "is_active": true
 * }
 * ```
 */
export async function getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/api/auth/me');
    setStoredUser(response.data);
    return response.data;
}


/**
 * Logout - Clear stored tokens and user data.
 * 
 * NOTE: This only clears client-side data. The JWT token itself
 * is still valid until it expires. For true logout, the backend
 * would need a token blacklist (not implemented in CloudSim).
 */
export function logout(): void {
    removeToken();
}


/**
 * Check if user has a stored token (appears authenticated).
 * 
 * NOTE: This doesn't verify the token is still valid.
 * The token could be expired. Use getCurrentUser() to verify.
 */
export function isAuthenticated(): boolean {
    return getToken() !== null;
}


// =============================================================================
// QUICK REFERENCE: COMPLETE LOGIN FLOW
// =============================================================================
/*
 * 1. Get a token by logging in:
 *    ```bash
 *    curl -X POST http://localhost:8000/api/auth/login \
 *      -H "Content-Type: application/x-www-form-urlencoded" \
 *      -d "username=admin@gmail.com&password=admin123"
 *    ```
 * 
 * 2. Copy the access_token from the response
 * 
 * 3. Use it in subsequent requests:
 *    ```bash
 *    export TOKEN="eyJhbGciOiJIUzI1NiIs..."
 *    
 *    curl -X GET http://localhost:8000/api/auth/me \
 *      -H "Authorization: Bearer $TOKEN"
 *    
 *    curl -X GET http://localhost:8000/api/ec2/instances \
 *      -H "Authorization: Bearer $TOKEN"
 *    ```
 */
