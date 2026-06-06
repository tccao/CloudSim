# CloudSim Frontend Learning Guide

A comprehensive guide to modern frontend development for Python developers, using the CloudSim project as a reference implementation. Includes interview preparation and hands-on exercises.

---

## Table of Contents

1.  [Technology Stack Overview](#technology-stack-overview)
2.  [TypeScript Fundamentals](#typescript-fundamentals)
3.  [React Core Concepts](#react-core-concepts)
4.  [State Management](#state-management)
5.  [Component Architecture](#component-architecture)
6.  [API Integration with Axios](#api-integration-with-axios)
7.  [Styling with Tailwind CSS](#styling-with-tailwind-css)
8.  [UI Component Libraries](#ui-component-libraries)
9.  [Build Tools (Vite)](#build-tools-vite)
10. [Interview Questions & Answers](#interview-questions--answers)
11. [Hands-On Exercises (CloudSim-Based)](#hands-on-exercises-cloudsim-based)
12. [Best Learning Resources](#best-learning-resources)

---

## Technology Stack Overview

The CloudSim frontend uses a modern, production-ready stack:

| Technology      | Purpose                       | Python Analog           |
| --------------- | ----------------------------- | ----------------------- |
| **TypeScript**  | Type-safe JavaScript          | Python type hints       |
| **React**       | UI component library          | Flask/Django templates  |
| **Vite**        | Build tool & dev server       | `python manage.py runserver` |
| **Tailwind CSS**| Utility-first CSS framework   | N/A (styling)           |
| **Axios**       | HTTP client                   | `requests` library      |
| **Radix UI**    | Accessible primitives         | N/A (UI components)     |
| **Recharts**    | Data visualization            | Matplotlib/Plotly       |

---

## TypeScript Fundamentals

### What is TypeScript?
TypeScript is a superset of JavaScript that adds static typing. Think of it as Python with type hints, but the hints are **required and enforced at compile time**.

### Key Syntax Comparison

```typescript
// TypeScript (CloudSim: frontend/src/api/ec2.ts)
interface EC2Instance {
    instance_id: string;
    name: string;
    state: string;
    public_ip: string | null;  // Union type: string OR null
}

async function getInstance(id: string): Promise<EC2Instance> {
    const response = await api.get<EC2Instance>(`/api/ec2/instances/${id}`);
    return response.data;
}
```

```python
# Python equivalent
from typing import Optional
from dataclasses import dataclass

@dataclass
class EC2Instance:
    instance_id: str
    name: str
    state: str
    public_ip: Optional[str]  # str or None

async def get_instance(id: str) -> EC2Instance:
    response = await api.get(f"/api/ec2/instances/{id}")
    return EC2Instance(**response.data)
```

### Key TypeScript Concepts

| Concept           | Example                                   | Python Equivalent           |
| ----------------- | ----------------------------------------- | --------------------------- |
| Interface         | `interface User { name: string; }`        | `@dataclass class User`     |
| Type              | `type State = 'running' \| 'stopped';`    | `Literal['running', 'stopped']` |
| Generics          | `Promise<T>`, `Array<User>`               | `list[User]`, `Dict[str, T]` |
| Optional          | `name?: string`                           | `Optional[str]`             |
| Union             | `string \| null`                          | `str \| None`               |

**📂 CloudSim Reference:** `frontend/src/api/ec2.ts` - All API interfaces

**📚 Resources:**
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) - Official docs
- [TypeScript for Python Developers](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes-oop.html)

---

## React Core Concepts

### What is React?
React is a library for building user interfaces using **components**. Instead of writing HTML templates, you write JavaScript functions that return UI.

### Components: Functions that Return UI

```tsx
// CloudSim: frontend/src/components/InstanceDetailsPage.tsx
export function InstanceDetailsPage({ instanceId }: InstanceDetailsPageProps) {
  // This is a COMPONENT - a function that returns JSX (HTML-like syntax)
  return (
    <div className="space-y-6">
      <h1>Instance Details</h1>
      <p>Viewing: {instanceId}</p>  {/* Curly braces = JavaScript expression */}
    </div>
  );
}
```

**Python Mental Model:** Think of each component as a function that generates an HTML template.

### JSX: HTML in JavaScript

JSX is the syntax that looks like HTML but lives inside JavaScript:

```tsx
// JSX (CloudSim pattern)
<Button onClick={() => handleClick()} className="bg-blue-500">
  Click Me
</Button>

// Compiles to:
React.createElement(Button, { onClick: () => handleClick(), className: "bg-blue-500" }, "Click Me")
```

### Props: Passing Data to Components

Props are function arguments for components. They flow **one-way: parent → child**.

```tsx
// CloudSim: frontend/src/App.tsx
// Parent component passes data DOWN to child
<DashboardPage onInstanceClick={handleInstanceClick} />

// CloudSim: frontend/src/components/DashboardPage.tsx
// Child receives and uses the prop
interface DashboardPageProps {
  onInstanceClick: (id: string) => void;
}

export function DashboardPage({ onInstanceClick }: DashboardPageProps) {
  return (
    <button onClick={() => onInstanceClick("i-123abc")}>
      View Instance
    </button>
  );
}
```

**📚 Resources:**
- [React Official Tutorial](https://react.dev/learn)
- [React in 100 Seconds (Video)](https://www.youtube.com/watch?v=Tn6-PIqc4UM)

---

## State Management

### useState: Local Component State

`useState` is React's way of storing data that can change over time.

```tsx
// CloudSim: frontend/src/components/InstanceDetailsPage.tsx
import { useState } from 'react';

export function InstanceDetailsPage() {
  // Declare state: [currentValue, setterFunction] = useState(initialValue)
  const [instance, setInstance] = useState<EC2InstanceDetails | null>(null);
  const [loading, setLoading] = useState(false);

  // Update state (triggers re-render)
  setLoading(true);
  setInstance(fetchedData);
  
  // Read state
  if (loading) return <Spinner />;
  return <div>{instance?.name}</div>;
}
```

**Python Mental Model:**
```python
# Python equivalent concept
class Component:
    def __init__(self):
        self.instance = None  # state
        self.loading = False  # state
    
    def set_loading(self, value):
        self.loading = value
        self.re_render()  # React does this automatically
```

### useEffect: Side Effects (API Calls, Timers)

`useEffect` runs code **after** the component renders. Perfect for API calls.

```tsx
// CloudSim: frontend/src/components/InstanceDetailsPage.tsx
import { useEffect } from 'react';

export function InstanceDetailsPage({ instanceId }) {
  const [instance, setInstance] = useState(null);

  useEffect(() => {
    // This runs AFTER render, when instanceId changes
    if (instanceId) {
      fetchInstanceDetails(instanceId);
    }
  }, [instanceId]);  // Dependency array: re-run when these change
  //  ^^^^^^^^^^^ IMPORTANT: Controls when effect runs
}
```

**Dependency Array Rules:**
| Dependency Array | When Effect Runs                    |
| ---------------- | ----------------------------------- |
| `[]`             | Once, on mount only                 |
| `[instanceId]`   | On mount + whenever `instanceId` changes |
| (omitted)        | After **every** render (usually wrong) |

### useContext: Global State Sharing

Context shares state across components without prop drilling.

```tsx
// CloudSim: frontend/src/contexts/UserContext.tsx
// 1. Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 2. Provider wraps the app
export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// 3. Consumer hook
export function useUser() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}

// 4. Usage in any component
function Header() {
  const { user, logout } = useUser();  // Access global state
  return <span>{user?.username}</span>;
}
```

**📂 CloudSim Reference:** `frontend/src/contexts/UserContext.tsx`

**📚 Resources:**
- [useState Guide](https://react.dev/reference/react/useState)
- [useEffect Guide](https://react.dev/reference/react/useEffect)
- [useContext Guide](https://react.dev/reference/react/useContext)

---

## Component Architecture

### File Structure Pattern

```
frontend/src/
├── api/                    # API client functions
│   ├── client.ts           # Axios instance configuration
│   ├── ec2.ts              # EC2 API calls
│   └── auth.ts             # Authentication API
├── components/             # UI Components
│   ├── ui/                 # Reusable primitives (Button, Card, etc.)
│   ├── DashboardPage.tsx   # Page-level components
│   └── InstanceDetailsPage.tsx
├── contexts/               # Global state (React Context)
│   └── UserContext.tsx
├── App.tsx                 # Root component (routing, layout)
└── main.tsx                # Entry point
```

### State Lifting Pattern (Used in CloudSim)

When two components need to share state, "lift" it to their common parent.

```
          App.tsx
         /       \
        ↓ props   ↓ props
   DashboardPage  InstanceDetailsPage
```

```tsx
// CloudSim: frontend/src/App.tsx
function AppContent() {
  // State lives in the PARENT
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);

  const handleInstanceClick = (id: string) => {
    setSelectedInstanceId(id);  // Update state
    setActiveTab("details");
  };

  return (
    <>
      {/* Pass callback DOWN to Dashboard */}
      <DashboardPage onInstanceClick={handleInstanceClick} />
      
      {/* Pass data DOWN to Details */}
      <InstanceDetailsPage instanceId={selectedInstanceId} />
    </>
  );
}
```

---

## API Integration with Axios

### Axios: HTTP Client (like Python's `requests`)

```tsx
// CloudSim: frontend/src/api/client.ts
import axios from 'axios';

export const api = axios.create({
    baseURL: 'http://localhost:8000',
    headers: { 'Content-Type': 'application/json' },
});
```

```tsx
// CloudSim: frontend/src/api/ec2.ts
export async function getInstance(instanceId: string): Promise<EC2InstanceDetails> {
    const response = await api.get<EC2InstanceDetails>(`/api/ec2/instances/${instanceId}`);
    return response.data;
}

// POST request example
export async function createInstance(data: CreateInstanceRequest): Promise<ActionResponse> {
    const response = await api.post<ActionResponse>('/api/ec2/instances', data);
    return response.data;
}
```

**Python Comparison:**
```python
# Python equivalent
import requests

def get_instance(instance_id: str) -> EC2Instance:
    response = requests.get(f"http://localhost:8000/api/ec2/instances/{instance_id}")
    return response.json()
```

### Async/Await Pattern

```tsx
// CloudSim: frontend/src/components/InstanceDetailsPage.tsx
const fetchInstanceDetails = async (id: string) => {
  setLoading(true);
  try {
    const data = await getInstance(id);  // Wait for API response
    setInstance(data);
  } catch (error) {
    console.error("Failed to fetch:", error);
    toast.error("Failed to load instance details");
  } finally {
    setLoading(false);
  }
};
```

**📚 Resources:**
- [Axios Documentation](https://axios-http.com/docs/intro)
- [Async/Await in JavaScript](https://javascript.info/async-await)

---

## Styling with Tailwind CSS

### What is Tailwind?
Tailwind CSS is a utility-first CSS framework. Instead of writing CSS files, you apply tiny classes directly in HTML/JSX.

```tsx
// CloudSim styling pattern
<div className="flex justify-between items-center gap-4 p-6 bg-white rounded-lg shadow-sm">
  <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
  <Button className="bg-orange-500 hover:bg-orange-600 text-white">
    Launch Instance
  </Button>
</div>
```

### Common Tailwind Classes

| Class              | CSS Equivalent              | Purpose            |
| ------------------ | --------------------------- | ------------------ |
| `flex`             | `display: flex`             | Flexbox container  |
| `grid grid-cols-4` | `display: grid; grid-template-columns: repeat(4, 1fr)` | Grid layout |
| `p-4`              | `padding: 1rem`             | Padding (4 = 16px) |
| `mt-2`             | `margin-top: 0.5rem`        | Margin top         |
| `text-sm`          | `font-size: 0.875rem`       | Small text         |
| `bg-gray-100`      | `background-color: #f3f4f6` | Background color   |
| `rounded-lg`       | `border-radius: 0.5rem`     | Rounded corners    |
| `hover:bg-blue-600`| On hover, change background | State variants     |

**📂 CloudSim Reference:** Any component file, e.g., `DashboardPage.tsx`

**📚 Resources:**
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Tailwind Cheat Sheet](https://tailwindcomponents.com/cheatsheet/)

---

## UI Component Libraries

### Radix UI + shadcn/ui

CloudSim uses **Radix UI** primitives wrapped by **shadcn/ui** for accessible, customizable components.

```tsx
// CloudSim: Using pre-built components
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';

<Tabs defaultValue="details">
  <TabsList>
    <TabsTrigger value="details">Details</TabsTrigger>
    <TabsTrigger value="security">Security</TabsTrigger>
  </TabsList>
  <TabsContent value="details">
    <Card className="p-6">Instance content here</Card>
  </TabsContent>
</Tabs>
```

### Lucide Icons

```tsx
// CloudSim: Icon usage
import { Play, Square, RotateCw, Loader2 } from 'lucide-react';

<Button>
  <Play className="h-4 w-4 mr-2" />  {/* Size + margin */}
  Start
</Button>
```

### Recharts (Data Visualization)

```tsx
// CloudSim: frontend/src/components/InstanceMonitoringPage.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={cpuData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="time" />
    <YAxis />
    <Tooltip />
    <Line type="monotone" dataKey="usage" stroke="#3b82f6" />
  </LineChart>
</ResponsiveContainer>
```

**📚 Resources:**
- [shadcn/ui Docs](https://ui.shadcn.com/)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- [Recharts Documentation](https://recharts.org/en-US/)

---

## Build Tools (Vite)

### What is Vite?
Vite is a modern build tool that provides:
- **Dev server** with hot module replacement (instant updates)
- **Production bundler** that optimizes code

```bash
# Development (instant reload)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Key Config Files

| File               | Purpose                                  |
| ------------------ | ---------------------------------------- |
| `package.json`     | Dependencies, scripts                    |
| `vite.config.ts`   | Build configuration                      |
| `tsconfig.json`    | TypeScript compiler options              |
| `index.html`       | Entry HTML file                          |

**📂 CloudSim Reference:** `frontend/vite.config.ts`, `frontend/package.json`

---

## Interview Questions & Answers

### 🔵 Junior Fullstack Questions (React/Frontend Focus)

#### Q1: What is the Virtual DOM and why does React use it?
**Answer:** The Virtual DOM is an in-memory JavaScript representation of the actual DOM. When state changes, React:
1. Creates a new Virtual DOM tree
2. Compares it with the previous one (diffing)
3. Updates only the changed parts in the real DOM (reconciliation)

**Why:** Direct DOM manipulation is slow. Batching changes improves performance.

**CloudSim Example:** When you click "Start" on an instance, only the state badge re-renders, not the entire page.

---

#### Q2: Explain the difference between `useState` and `useEffect`
**Answer:**
- **useState:** Stores data that persists across renders and triggers re-renders when updated
- **useEffect:** Runs side effects (API calls, subscriptions) after render

**CloudSim Example:**
```tsx
// InstanceDetailsPage.tsx
const [instance, setInstance] = useState(null);   // Data storage
const [loading, setLoading] = useState(false);    // UI state

useEffect(() => {
  fetchInstanceDetails(instanceId);  // Side effect: API call
}, [instanceId]);  // Runs when instanceId changes
```

---

#### Q3: What is "prop drilling" and how do you solve it?
**Answer:** Prop drilling is passing props through many component levels to reach a deeply nested child.

**Solutions:**
1. **Context API** (used in CloudSim for auth)
2. State management libraries (Redux, Zustand)
3. Component composition

**CloudSim Example:** User authentication uses Context to avoid drilling:
```tsx
// Any component can access user without prop drilling
const { user, logout } = useUser();
```

---

#### Q4: Explain controlled vs uncontrolled components
**Answer:**
- **Controlled:** React state manages the input value (`value={state}` + `onChange`)
- **Uncontrolled:** DOM manages its own state (accessed via `ref`)

**CloudSim Example (Controlled):**
```tsx
// CreateInstanceModal.tsx (conceptual)
const [name, setName] = useState('');
<input value={name} onChange={(e) => setName(e.target.value)} />
```

---

#### Q5: How do you handle API errors in React?
**Answer:** Use try/catch with async/await and display error feedback to users.

**CloudSim Example:**
```tsx
// InstanceDetailsPage.tsx
const fetchInstanceDetails = async (id: string) => {
  setLoading(true);
  try {
    const data = await getInstance(id);
    setInstance(data);
  } catch (error) {
    console.error("Failed:", error);
    toast.error("Failed to load instance");  // User feedback
  } finally {
    setLoading(false);
  }
};
```

---

#### Q6: What is the purpose of the dependency array in useEffect?
**Answer:** It controls when the effect runs:
- `[]` - Run once on mount
- `[dep1, dep2]` - Run when any dependency changes
- Omitted - Run after every render (usually a bug)

**CloudSim Example:**
```tsx
useEffect(() => {
  if (instanceId) {
    fetchInstanceDetails(instanceId);
  }
}, [instanceId]);  // Only re-fetch when user selects a different instance
```

---

#### Q7: How do you share state between sibling components?
**Answer:** "Lift state up" to the nearest common parent.

**CloudSim Example:**
```
App.tsx (holds selectedInstanceId)
├── DashboardPage (calls onInstanceClick → updates parent state)
└── InstanceDetailsPage (receives instanceId as prop)
```

---

### 🟢 Fullstack Questions (Frontend + Backend)

#### Q8: How does the frontend communicate with the backend in CloudSim?
**Answer:** Via RESTful API calls using Axios:
1. Frontend calls API function (e.g., `getInstance(id)`)
2. Axios sends HTTP request to FastAPI backend
3. Backend queries AWS/database and returns JSON
4. Frontend updates state with response data

---

#### Q9: How do you handle authentication tokens?
**Answer:** Store token in localStorage, attach to requests via Axios interceptors.

**CloudSim Flow:**
1. User logs in → Backend returns JWT token
2. Token stored in localStorage
3. Axios interceptor adds `Authorization: Bearer <token>` to all requests
4. Backend validates token on protected routes

---

#### Q10: What happens when a user clicks an instance name in CloudSim?
**Answer (trace the flow):**
1. `DashboardPage`: `onClick={() => onInstanceClick(instance.id)}`
2. `App.tsx`: `setSelectedInstanceId(id)` + `setActiveTab("details")`
3. `InstanceDetailsPage`: `useEffect` detects `instanceId` change
4. `fetchInstanceDetails(id)` calls `getInstance(id)`
5. `api/ec2.ts`: `api.get(`/api/ec2/instances/${id}`)`
6. Backend: `aws_service.get_instance()` calls AWS API
7. Response flows back, `setInstance(data)` triggers re-render

---

## Hands-On Exercises (CloudSim-Based)

These exercises use your actual CloudSim codebase. Complete them to solidify concepts.

---

### Exercise 1: Add a Refresh Button (useState + API Call)
**Difficulty:** ⭐ Easy | **Concepts:** useState, onClick handlers, API calls

**Task:** Add a "Refresh" button to `InstanceDetailsPage` that re-fetches the instance data.

**Steps:**
1. Open `frontend/src/components/InstanceDetailsPage.tsx`
2. Add a button in the header section next to "Terminate"
3. On click, call `fetchInstanceDetails(instance.instance_id)`
4. Show a loading spinner while refreshing

**Starter Code:**
```tsx
<Button 
  variant="outline" 
  size="sm" 
  onClick={() => fetchInstanceDetails(instance.instance_id)}
  disabled={loading}
>
  <RotateCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
  Refresh
</Button>
```

**Interview Connection:** "Describe how you'd implement a refresh feature with loading state."

---

### Exercise 2: Display Instance Uptime (Data Transformation)
**Difficulty:** ⭐ Easy | **Concepts:** Data manipulation, date formatting

**Task:** Calculate and display how long the instance has been running.

**Steps:**
1. In `InstanceDetailsPage`, create a function to calculate uptime:
```tsx
const calculateUptime = (launchTime: string | null): string => {
  if (!launchTime) return '-';
  const launched = new Date(launchTime);
  const now = new Date();
  const diffMs = now.getTime() - launched.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  return `${days}d ${hours}h`;
};
```
2. Display it in the Details tab

**Interview Connection:** "How would you format dates and calculate time differences in JavaScript?"

---

### Exercise 3: Add Search/Filter to Dashboard (Controlled Input)
**Difficulty:** ⭐⭐ Medium | **Concepts:** Controlled components, array filtering

**Task:** Add a search box to filter instances by name.

**Steps:**
1. Open `frontend/src/components/DashboardPage.tsx`
2. Add state: `const [searchTerm, setSearchTerm] = useState('')`
3. Add a search input:
```tsx
<input
  type="text"
  placeholder="Search instances..."
  value={searchTerm}
  onChange={(e) => setSearchTerm(e.target.value)}
  className="px-3 py-2 border rounded-lg"
/>
```
4. Filter the instances:
```tsx
const filteredInstances = instances.filter(i => 
  i.name.toLowerCase().includes(searchTerm.toLowerCase())
);
```
5. Render `filteredInstances` instead of `instances`

**Interview Connection:** "Implement a search feature with real-time filtering."

---

### Exercise 4: Add Confirmation Dialog for Terminate (Component Composition)
**Difficulty:** ⭐⭐ Medium | **Concepts:** Dialogs, state management, user confirmation

**Task:** Replace the `confirm()` with a proper modal dialog before terminating.

**Steps:**
1. Create state for dialog visibility:
```tsx
const [showTerminateDialog, setShowTerminateDialog] = useState(false);
```
2. Use the existing AlertDialog component from shadcn/ui
3. On "Terminate" click, show dialog instead of browser confirm
4. On dialog confirm, call `handleTerminate()`

**Reference:** Look at how `CreateInstanceModal.tsx` handles open/close state.

**Interview Connection:** "How would you implement a confirmation flow with proper UX?"

---

### Exercise 5: Create an Instance Status Indicator Component (Component Extraction)
**Difficulty:** ⭐⭐ Medium | **Concepts:** Reusable components, props

**Task:** Extract the state badge into a reusable `InstanceStatusBadge` component.

**Steps:**
1. Create `frontend/src/components/InstanceStatusBadge.tsx`:
```tsx
import { Badge } from './ui/badge';

interface InstanceStatusBadgeProps {
  state: string;
}

export function InstanceStatusBadge({ state }: InstanceStatusBadgeProps) {
  const colorClasses = {
    running: 'bg-green-600',
    stopped: 'bg-gray-500',
    pending: 'bg-yellow-500',
    terminated: 'bg-red-500',
  };
  
  return (
    <Badge className={colorClasses[state as keyof typeof colorClasses] || 'bg-gray-400'}>
      {state}
    </Badge>
  );
}
```
2. Replace hardcoded badges in `DashboardPage` and `InstanceDetailsPage`

**Interview Connection:** "How do you decide when to extract a component?"

---

### Exercise 6: Add a New Tab to Instance Details (Tabs + New Feature)
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Full feature implementation

**Task:** Add an "Events" tab showing recent instance events (mock data initially).

**Steps:**
1. In `InstanceDetailsPage.tsx`, add a new `TabsTrigger` for "Events"
2. Create mock event data:
```tsx
const mockEvents = [
  { timestamp: '2026-01-01T12:00:00Z', type: 'StateChange', message: 'Instance started' },
  { timestamp: '2026-01-01T11:55:00Z', type: 'StatusCheck', message: 'System reachability check passed' },
];
```
3. Create a `TabsContent` with a table displaying events
4. **Bonus:** Add backend endpoint and fetch real events

**Interview Connection:** "Walk me through adding a new feature from frontend to backend."

---

### Exercise 7: Implement Auto-Refresh for Metrics (useEffect + Intervals)
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Intervals, cleanup, useEffect

**Task:** Auto-refresh metrics data every 30 seconds on the Monitoring page.

**Steps:**
1. Open `frontend/src/components/InstanceMonitoringPage.tsx`
2. Add interval in useEffect:
```tsx
useEffect(() => {
  const interval = setInterval(() => {
    if (selectedInstance) {
      loadMetrics();  // Your existing function
    }
  }, 30000);  // 30 seconds
  
  return () => clearInterval(interval);  // CLEANUP! Important!
}, [selectedInstance]);
```

**Interview Connection:** "How do you handle intervals in React? What's the cleanup function for?"

---

### Exercise 8: Add Error Boundary (Error Handling)
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Error boundaries, class components

**Task:** Wrap the app in an Error Boundary to catch rendering errors.

**Steps:**
1. Create `frontend/src/components/ErrorBoundary.tsx`:
```tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center">
          <h2>Something went wrong.</h2>
          <button onClick={() => window.location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```
2. Wrap `<App />` in `main.tsx`

**Interview Connection:** "How do you handle unexpected errors in React?"

---

### Exercise 9: Add Role-Based Button Visibility (Conditional Rendering)
**Difficulty:** ⭐⭐ Medium | **Concepts:** Context, conditional rendering, authorization

**Task:** Only show "Terminate" button to Admin users.

**Steps:**
1. In `InstanceDetailsPage`, import `useUser`:
```tsx
import { useUser } from '../contexts/UserContext';
```
2. Get user role:
```tsx
const { user } = useUser();
```
3. Conditionally render:
```tsx
{user?.role === 'Admin' && (
  <Button onClick={handleTerminate} className="text-red-600">
    <Trash2 className="h-4 w-4 mr-2" />
    Terminate
  </Button>
)}
```

**Interview Connection:** "How do you implement role-based access control in the frontend?"

---

### Exercise 10: Write a Unit Test (Testing)
**Difficulty:** ⭐⭐⭐ Hard | **Concepts:** Testing, Jest, React Testing Library

**Task:** Write a test for the `InstanceStatusBadge` component.

**Steps:**
1. Create `frontend/src/components/__tests__/InstanceStatusBadge.test.tsx`
2. Test that it renders the correct color for each state:
```tsx
import { render, screen } from '@testing-library/react';
import { InstanceStatusBadge } from '../InstanceStatusBadge';

describe('InstanceStatusBadge', () => {
  it('renders running state with green background', () => {
    render(<InstanceStatusBadge state="running" />);
    const badge = screen.getByText('running');
    expect(badge).toHaveClass('bg-green-600');
  });

  it('renders stopped state with gray background', () => {
    render(<InstanceStatusBadge state="stopped" />);
    const badge = screen.getByText('stopped');
    expect(badge).toHaveClass('bg-gray-500');
  });
});
```

**Interview Connection:** "What testing strategies do you use for React components?"

---

## Exercise Progress Tracker

| # | Exercise | Status | Concepts Practiced |
|---|----------|--------|-------------------|
| 1 | Refresh Button | ☐ | useState, onClick, API |
| 2 | Instance Uptime | ☐ | Date manipulation |
| 3 | Dashboard Search | ☐ | Controlled inputs, filtering |
| 4 | Terminate Dialog | ☐ | Modal state, composition |
| 5 | Status Badge Component | ☐ | Component extraction |
| 6 | Events Tab | ☐ | Full feature implementation |
| 7 | Auto-Refresh Metrics | ☐ | Intervals, cleanup |
| 8 | Error Boundary | ☐ | Error handling |
| 9 | Role-Based Visibility | ☐ | Auth, conditional rendering |
| 10 | Unit Testing | ☐ | Jest, Testing Library |

---

## Best Learning Resources

### Free Courses
1. **[React Official Tutorial](https://react.dev/learn)** - Start here
2. **[JavaScript.info](https://javascript.info/)** - JS fundamentals
3. **[TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)** - TS basics

### Video Tutorials
1. **[Fireship React in 100 Seconds](https://www.youtube.com/watch?v=Tn6-PIqc4UM)** - Quick overview
2. **[Codevolution React Complete Course](https://www.youtube.com/playlist?list=PLC3y8-rFHvwgg3vaYJgHGnModB54rxOk3)** - Comprehensive
3. **[Net Ninja React Query Course](https://www.youtube.com/playlist?list=PL4cUxeGkcC9jERUGvbudErNCeSZHWUVlb)** - Data fetching

### Documentation (Keep Bookmarked)
- [React Docs](https://react.dev/)
- [TypeScript Docs](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [MDN Web Docs](https://developer.mozilla.org/) - JavaScript reference

### Practice Projects
1. Build a Todo app with useState/useEffect
2. Add a backend API and use Axios
3. Implement authentication with Context
4. Add data visualization with Recharts

---

## Quick Reference: CloudSim File Map

```
frontend/src/
├── App.tsx                          # Root: Contains tab navigation, state lifting
├── main.tsx                         # Entry: Renders App to DOM
├── api/
│   ├── client.ts                    # Axios instance (baseURL, headers)
│   ├── ec2.ts                       # EC2 API (getInstance, listInstances, etc.)
│   └── auth.ts                      # Authentication API
├── components/
│   ├── ui/                          # Reusable: Button, Card, Table, Badge, etc.
│   ├── DashboardPage.tsx            # Dashboard with instance list
│   ├── InstanceDetailsPage.tsx      # Detail view fetching from API
│   ├── InstanceMonitoringPage.tsx   # Charts and metrics
│   ├── LoginModal.tsx               # Authentication UI
│   └── CreateInstanceModal.tsx      # Instance creation form
└── contexts/
    └── UserContext.tsx              # Global auth state (createContext pattern)
```

---

*Generated for CloudSim - A cloud infrastructure management application built with React, TypeScript, and Tailwind CSS.*
