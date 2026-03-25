# GenAI Observability Platform - Frontend

React-based dashboard for monitoring and analyzing GenAI agents.

## Features

- **Dashboard**: Overview of system health, metrics, and recent activity
- **Traces**: Browse and search execution traces with timeline visualization
- **Agents**: Manage and monitor registered agents
- **Alerts**: View and manage alerts with investigation results
- **Settings**: Configure API keys, thresholds, and notifications

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Router** - Navigation
- **Recharts** - Data visualization
- **SWR** - Data fetching with caching
- **Zustand** - State management
- **Heroicons** - Icons

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=https://your-api-endpoint.execute-api.us-east-1.amazonaws.com
```

## Project Structure

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── components/          # Shared UI components
│   │   ├── Layout.tsx       # Main layout with sidebar
│   │   ├── Card.tsx         # Card components
│   │   ├── Charts.tsx       # Chart components (Line, Area, Bar)
│   │   ├── Table.tsx        # Table with pagination
│   │   ├── Badge.tsx        # Status and severity badges
│   │   └── TimeRangeSelector.tsx
│   ├── pages/               # Page components
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── Traces.tsx       # Trace list
│   │   ├── TraceDetail.tsx  # Single trace view
│   │   ├── Agents.tsx       # Agent list
│   │   ├── AgentDetail.tsx  # Single agent view
│   │   ├── Alerts.tsx       # Alert management
│   │   └── Settings.tsx     # Configuration
│   ├── lib/                 # Utilities and services
│   │   ├── api.ts           # API client
│   │   ├── hooks.ts         # React hooks (data fetching)
│   │   └── utils.ts         # Helper functions
│   ├── types/               # TypeScript types
│   │   └── index.ts
│   ├── App.tsx              # Main app component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── index.html
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
└── vite.config.ts
```

## Pages

### Dashboard (`/`)

Overview page showing:
- Key metrics (agents, traces, errors, latency, tokens, cost)
- Latency and request volume charts
- Recent alerts
- Top agents by activity

### Traces (`/traces`)

- Searchable list of execution traces
- Filter by status, agent, time range
- Click through to detailed trace view

### Trace Detail (`/traces/:traceId`)

- Trace overview and metadata
- Visual timeline of spans
- Detailed span information with attributes

### Agents (`/agents`)

- List of registered agents
- Status indicators
- Quick metrics per agent

### Agent Detail (`/agents/:agentId`)

- Agent configuration and metadata
- Performance metrics and charts
- Recent traces and alerts

### Alerts (`/alerts`)

- List of alerts with severity indicators
- Filter by status, severity, agent
- Investigation results from LLM
- Acknowledge and resolve actions

### Settings (`/settings`)

- API key configuration
- Alert threshold settings
- Notification channel management
- System health status

## Components

### Layout

Main layout with responsive sidebar navigation.

### Card

```tsx
<Card>
  <CardHeader title="Title" subtitle="Description" />
  {/* Content */}
</Card>

<StatCard
  title="Metric Name"
  value="123"
  trend={{ value: 5, direction: 'up' }}
  icon={ChartIcon}
/>
```

### Charts

```tsx
<MetricLineChart
  data={data}
  lines={[
    { key: 'value', color: '#3b82f6', name: 'Avg' },
    { key: 'p95', color: '#f59e0b', name: 'P95' },
  ]}
  height={300}
/>

<MetricAreaChart data={data} color="#10b981" height={300} />

<MetricBarChart data={data} color="#8b5cf6" height={300} />
```

### Table

```tsx
<Table
  data={items}
  columns={[
    { key: 'id', header: 'ID', render: (item) => <span>{item.id}</span> },
    { key: 'name', header: 'Name' },
  ]}
  loading={isLoading}
/>
<Pagination
  currentPage={page}
  totalPages={totalPages}
  onPageChange={setPage}
/>
```

### Badge

```tsx
<StatusBadge status="completed" />
<SeverityBadge severity="critical" />
<Badge className="badge-primary">Custom</Badge>
```

## API Integration

The frontend uses SWR for data fetching with automatic caching and revalidation.

```tsx
// Using hooks
const { data, isLoading, error } = useTraces(filters, page, pageSize)
const { data: agent } = useAgent(agentId)
const { data: metrics } = useDashboardMetrics(timeRange)

// Mutations
const { acknowledgeAlert, resolveAlert } = useAlertActions()
```

## Styling

Uses TailwindCSS with custom configuration:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: colors.blue,
      },
    },
  },
}
```

Custom utility classes are defined in `index.css`:
- `.btn-primary`, `.btn-secondary` - Button styles
- `.input` - Input field styles
- `.badge`, `.badge-success`, `.badge-error`, `.badge-warning` - Badge styles
- `.card` - Card container

## Development

### Running Tests

```bash
npm run test
```

### Linting

```bash
npm run lint
```

### Building

```bash
npm run build
```

Output is generated in the `dist/` directory.

## Deployment

### Static Hosting

Build the project and deploy the `dist/` folder to any static hosting:
- AWS S3 + CloudFront
- Vercel
- Netlify
- GitHub Pages

### Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### AWS Amplify

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```
