import { useState } from 'react'
import {
  CpuChipIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CurrencyDollarIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Card, CardHeader, StatCard, MetricAreaChart, MetricLineChart } from '../components'
import { TimeRangeSelector } from '../components/TimeRangeSelector'
import { useDashboardMetrics, useMetricsSeries, useAlerts } from '../lib/hooks'
import { formatNumber, formatCompact, formatCurrency, formatDuration } from '../lib/utils'
import { TimeRange } from '../types'
import { SeverityBadge, StatusBadge } from '../components/Badge'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')

  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics(timeRange)
  const { data: latencySeries, isLoading: latencyLoading } = useMetricsSeries('latency', timeRange)
  const { data: requestsSeries, isLoading: requestsLoading } = useMetricsSeries('requests', timeRange)
  const { data: alerts } = useAlerts({ status: 'open' }, 1, 5)

  // Demo data for charts when API not available
  const demoLatencyData = Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    value: 200 + Math.random() * 100,
    p95: 400 + Math.random() * 150,
  }))

  const demoRequestsData = Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    value: 1000 + Math.random() * 500,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Overview of your GenAI agents and system health
          </p>
        </div>
        <div className="w-48">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Total Agents"
          value={metrics?.total_agents ?? 12}
          subtitle={`${metrics?.active_agents ?? 10} active`}
          icon={CpuChipIcon}
        />
        <StatCard
          title="Total Traces"
          value={formatCompact(metrics?.total_traces ?? 45230)}
          subtitle="Last 24h"
          icon={ChartBarIcon}
        />
        <StatCard
          title="Error Count"
          value={formatNumber(metrics?.total_errors ?? 23)}
          trend={{ value: 12, direction: 'down' }}
          icon={ExclamationTriangleIcon}
        />
        <StatCard
          title="Avg Latency"
          value={formatDuration(metrics?.avg_latency_ms ?? 342)}
          trend={{ value: 5, direction: 'up' }}
          icon={ClockIcon}
        />
        <StatCard
          title="Total Tokens"
          value={formatCompact(metrics?.total_tokens ?? 2450000)}
          subtitle="Last 24h"
          icon={SparklesIcon}
        />
        <StatCard
          title="Total Cost"
          value={formatCurrency(metrics?.total_cost ?? 124.56)}
          subtitle="Last 24h"
          icon={CurrencyDollarIcon}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Response Latency" subtitle="Average and P95 latency over time" />
          <MetricLineChart
            data={latencySeries?.data ?? demoLatencyData}
            loading={latencyLoading}
            lines={[
              { key: 'value', color: '#3b82f6', name: 'Avg Latency' },
              { key: 'p95', color: '#f59e0b', name: 'P95 Latency' },
            ]}
            height={280}
          />
        </Card>

        <Card>
          <CardHeader title="Request Volume" subtitle="Total requests over time" />
          <MetricAreaChart
            data={requestsSeries?.data ?? demoRequestsData}
            loading={requestsLoading}
            color="#10b981"
            height={280}
          />
        </Card>
      </div>

      {/* Recent Alerts & Top Agents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <Card>
          <CardHeader
            title="Recent Alerts"
            subtitle="Open alerts requiring attention"
            action={
              <Link to="/alerts" className="text-sm text-primary-600 hover:text-primary-700">
                View all
              </Link>
            }
          />
          <div className="space-y-3">
            {(alerts?.items ?? demoAlerts).slice(0, 5).map((alert) => (
              <div
                key={alert.alert_id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <SeverityBadge severity={alert.severity} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{alert.anomaly_type}</p>
                    <p className="text-xs text-gray-500">{alert.agent_id}</p>
                  </div>
                </div>
                <StatusBadge status={alert.status} />
              </div>
            ))}
            {(!alerts?.items || alerts.items.length === 0) && (
              <p className="text-sm text-gray-500 text-center py-4">No open alerts</p>
            )}
          </div>
        </Card>

        {/* Top Agents by Activity */}
        <Card>
          <CardHeader
            title="Top Agents"
            subtitle="Most active agents by request count"
            action={
              <Link to="/agents" className="text-sm text-primary-600 hover:text-primary-700">
                View all
              </Link>
            }
          />
          <div className="space-y-3">
            {demoTopAgents.map((agent, index) => (
              <div
                key={agent.agent_id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <span className="flex items-center justify-center w-6 h-6 text-xs font-medium text-primary-700 bg-primary-100 rounded-full">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{agent.name}</p>
                    <p className="text-xs text-gray-500">{agent.framework}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {formatCompact(agent.requests)}
                  </p>
                  <p className="text-xs text-gray-500">requests</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

// Demo data
const demoAlerts = [
  {
    alert_id: '1',
    agent_id: 'agent-prod-001',
    anomaly_type: 'high_error_rate',
    severity: 'critical',
    status: 'open',
    timestamp: new Date().toISOString(),
    message: 'Error rate exceeded threshold',
  },
  {
    alert_id: '2',
    agent_id: 'agent-prod-002',
    anomaly_type: 'high_latency',
    severity: 'warning',
    status: 'acknowledged',
    timestamp: new Date().toISOString(),
    message: 'Latency spike detected',
  },
]

const demoTopAgents = [
  { agent_id: '1', name: 'Customer Support Bot', framework: 'LangChain', requests: 15230 },
  { agent_id: '2', name: 'Data Analysis Agent', framework: 'CrewAI', requests: 12450 },
  { agent_id: '3', name: 'Content Generator', framework: 'LangChain', requests: 9870 },
  { agent_id: '4', name: 'Code Assistant', framework: 'Custom', requests: 7650 },
  { agent_id: '5', name: 'Research Agent', framework: 'CrewAI', requests: 5430 },
]
