import axios from 'axios';

// ---------------------------------------------------------------------------
// Axios instance — single source of truth for all API calls
//
// WHY one instance?
//   Interceptors are registered PER instance. If you create multiple instances
//   (e.g., one in auth.ts, one in client.ts), only the one that had .use()
//   called on it will attach the token. By having one shared instance here,
//   every import of `api` gets the interceptors automatically — no implicit
//   import-order dependency.
//
// VITE_API_URL:
//   In development → undefined → falls back to localhost:8000
//   In production  → set to https://your-backend.onrender.com
//   Set in the Vercel project environment variables.
// ---------------------------------------------------------------------------

const TOKEN_KEY = 'cloudsim_access_token';

export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// ---------------------------------------------------------------------------
// REQUEST INTERCEPTOR — attach JWT token to every outgoing request
//
// Before every HTTP request, this adds:
//   Authorization: Bearer eyJhbGci...
//
// If there is no token (user not logged in), the header is simply omitted.
// The backend will return 401, which the response interceptor handles below.
// ---------------------------------------------------------------------------
api.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// ---------------------------------------------------------------------------
// RESPONSE INTERCEPTOR — handle expired/invalid tokens globally
//
// If ANY request returns 401 Unauthorized:
//   1. Clear the stored token (it's no longer valid)
//   2. Dispatch a custom event so the UI can react (show login modal)
//
// WHY a custom event instead of directly calling a React function?
//   This file is plain TypeScript — it has no access to React state or context.
//   The custom event is a clean way to communicate with the React layer without
//   creating a circular dependency.
// ---------------------------------------------------------------------------
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            // Notify the React app to show the login screen
            window.dispatchEvent(new CustomEvent('auth:logout'));
        }
        return Promise.reject(error);
    }
);
