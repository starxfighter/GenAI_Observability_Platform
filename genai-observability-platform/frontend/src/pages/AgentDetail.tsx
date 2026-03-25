import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { Card, CardHeader, StatCard, StatusBadge, MetricLineChart, MetricAreaChart } from '../components'
import { TimeRangeSelector } from '../components/TimeRangeSelector'
import { useAgent, useAgentMetrics, useTraces, useAlerts } from '../lib/hooks'
import { formatDate, formatDuration, formatCompact, formatCurrency, formatPercentage } from '../lib/utils'
import { TimeRange } from '../types'

export default function AgentDetail() {
  const { agentId } = useParams<{ agentId: string }>()
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')

  const { data: agent, isLoading: agentLoading } = useAgent(agentId)
  const { data: metrics } = useAgentMetrics(agentId, timeRange)
  const { data: traces } = useTraces({ agent_id: agentId }, 1, 5)
  const { data: alerts } = useAlerts({ agent_id: agentId, status: 'open' }, 1, 5)

  // Demo data
  const demoAgent = {
    agent_id: agentId ?? 'customer-support-bot',
    name: 'Customer Support Bot',
    framework: 'LangChain',
    version: '1.2.3',
    status: 'active' as const,
    last_seen: new Date(Date.now() - 60000).toISOString(),
    created_at: new Date(Date.now() - 30 * 24 * 3600000).toISOString(),
    metadata: {
      environment: 'production',
      team: 'support',
      owner: 'support-team@company.com',
      description: 'Handles customer inquiries and support tickets',
    },
  }

  const demoMetrics = {
    agent_id: agentId ?? 'customer-support-bot',
    period: timeRange,
    request_count: 15230,
    error_count: 45,
    error_rate: 0.003,
    avg_latency_ms: 342,
    p50_latency_ms: 280,
    p95_latency_ms: 650,
    p99_latency_ms: 1200,
    total_tokens: 2450000,
    total_cost: 124.56,
  }

  const demoLatencyData = Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    value: 300 + Math.random() * 100,
    p95: 600 + Math.random() * 200,
  }))

  const demoRequestsData = Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    value: 500 + Math.random() * 200,
  }))

  const displayAgent = agent ?? demoAgent
  const displayMetrics = metrics ?? demoMetrics

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading agent...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/agents"
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{displayAgent.name}</h1>
              <StatusBadge status={displayAgent.status} />
            </div>
            <p className="text-sm text-gray-500 font-mono">{displayAgent.agent_id}</p>
          </div>
        </div>
        <div className="w-48">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Agent Info */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-xs text-gray-500">Framework</p>
          <p className="text-sm font-medium text-gray-900">{displayAgent.framework}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500">Version</p>
          <p className="text-sm font-medium text-gray-900">{displayAgent.version}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500">Created</p>
          <p className="text-sm font-medium text-gray-900">{formatDate(displayAgent.created_at, 'PP')}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500">Last Seen</p>
          <p className="text-sm font-medium text-gray-900">{formatDate(displayAgent.last_seen, 'PPp')}</p>
        </Card>
      </div>

      {/* Metrics Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          title="Requests"
          value={formatCompact(displayMetrics.request_count)}
          subtitle={`Last ${timeRange}`}
        />
        <StatCard
          title="Errors"
          value={displayMetrics.error_count}
          subtitle={formatPercentage(displayMetrics.error_rate)}
        />
        <StatCard
          title="Avg Latency"
          value={formatDuration(displayMetrics.avg_latency_ms)}
        />
        <StatCard
          title="P95 Latency"
          value={formatDuration(displayMetrics.p95_latency_ms)}
        />
        <StatCard
          title="Tokens"
          value={formatCompact(displayMetrics.total_tokens)}
        />
        <StatCard
          title="Cost"
          value={formatCurrency(displayMetrics.total_cost)}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Latency" subtitle="Response time over the selected period" />
          <MetricLineChart
            data={demoLatencyData}
            lines={[
              { key: 'value', color: '#3b82f6', name: 'Avg' },
              { key: 'p95', color: '#f59e0b', name: 'P95' },
            ]}
            height={250}
          />
        </Card>
        <Card>
          <CardHeader title="Request Volume" subtitle="Requests over the selected period" />
          <MetricAreaChart data={demoRequestsData} color="#10b981" height={250} />
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Traces */}
        <Card>
          <CardHeader
            title="Recent Traces"
            action={
              <Link
                to={`/traces?agent_id=${agentId}`}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                View all
              </Link>
            }
          />
          <div className="space-y-3">
            {(traces?.items ?? demoTraces).slice(0, 5).map((trace) => (
              <Link
                key={trace.trace_id}
                to={`/traces/${trace.trace_id}`}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{trace.name}</p>
                  <p className="text-xs text-gray-500">{formatDate(trace.start_time, 'PPp')}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">
                    {formatDuration(trace.duration_ms ?? 0)}
                  </span>
                  <StatusBadge status={trace.status} />
                </div>
              </Link>
            ))}
          </div>
        </Card>

        {/* Open Alerts */}
        <Card>
          <CardHeader
            title="Open Alerts"
            action={
              <Link
                to={`/alerts?agent_id=${agentId}`}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                View all
              </Link>
            }
          />
          <div className="space-y-3">
            {(alerts?.items ?? []).length > 0 ? (
              alerts?.items.slice(0, 5).map((alert) => (
                <div
                  key={alert.alert_id}
                  className="p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900">{alert.anomaly_type}</span>
                    <StatusBadge status={alert.severity} />
                  </div>
                  <p className="text-xs text-gray-500">{formatDate(alert.timestamp, 'PPp')}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No open alerts</p>
            )}
          </div>
        </Card>
      </div>

      {/* Metadata */}
      {displayAgent.metadata && (
        <Card>
          <CardHeader title="Metadata" subtitle="Agent configuration and context" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(displayAgent.metadata).map(([key, value]) => (
              <div key={key}>
                <p className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                <p className="text-sm font-medium text-gray-900">{String(value)}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

const demoTraces = [
  {
    trace_id: 'trace-001',
    name: 'Customer inquiry processing',
    start_time: new Date(Date.now() - 300000).toISOString(),
    duration_ms: 1500,
    status: 'completed' as const,
  },
  {
    trace_id: 'trace-002',
    name: 'Support ticket analysis',
    start_time: new Date(Date.now() - 600000).toISOString(),
    duration_ms: 2300,
    status: 'completed' as const,
  },
  {
    trace_id: 'trace-003',
    name: 'FAQ response generation',
    start_time: new Date(Date.now() - 900000).toISOString(),
    duration_ms: 890,
    status: 'error' as const,
  },
]
