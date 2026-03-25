import { useParams, Link } from 'react-router-dom'
import { ArrowLeftIcon, ClockIcon, CpuChipIcon } from '@heroicons/react/24/outline'
import { Card, CardHeader, StatusBadge } from '../components'
import { useTrace } from '../lib/hooks'
import { formatDate, formatDuration, cn } from '../lib/utils'
import { Span } from '../types'

export default function TraceDetail() {
  const { traceId } = useParams<{ traceId: string }>()
  const { data: trace, isLoading } = useTrace(traceId)

  // Demo data
  const demoTrace = {
    trace_id: traceId ?? 'trace-abc123def456',
    agent_id: 'customer-support-bot',
    name: 'Customer inquiry processing',
    start_time: new Date(Date.now() - 300000).toISOString(),
    end_time: new Date(Date.now() - 298500).toISOString(),
    duration_ms: 1500,
    status: 'completed' as const,
    spans: [
      {
        span_id: 'span-001',
        trace_id: traceId ?? 'trace-abc123def456',
        name: 'process_request',
        span_type: 'execution' as const,
        start_time: new Date(Date.now() - 300000).toISOString(),
        end_time: new Date(Date.now() - 299800).toISOString(),
        duration_ms: 200,
        status: 'completed' as const,
        attributes: { input_length: 150 },
      },
      {
        span_id: 'span-002',
        trace_id: traceId ?? 'trace-abc123def456',
        parent_span_id: 'span-001',
        name: 'llm_call',
        span_type: 'llm' as const,
        start_time: new Date(Date.now() - 299800).toISOString(),
        end_time: new Date(Date.now() - 299000).toISOString(),
        duration_ms: 800,
        status: 'completed' as const,
        attributes: {
          model: 'claude-sonnet-4-20250514',
          input_tokens: 450,
          output_tokens: 230,
          temperature: 0.7,
        },
      },
      {
        span_id: 'span-003',
        trace_id: traceId ?? 'trace-abc123def456',
        parent_span_id: 'span-001',
        name: 'search_knowledge_base',
        span_type: 'tool' as const,
        start_time: new Date(Date.now() - 299000).toISOString(),
        end_time: new Date(Date.now() - 298700).toISOString(),
        duration_ms: 300,
        status: 'completed' as const,
        attributes: { query: 'product pricing', results_count: 5 },
      },
      {
        span_id: 'span-004',
        trace_id: traceId ?? 'trace-abc123def456',
        parent_span_id: 'span-001',
        name: 'format_response',
        span_type: 'execution' as const,
        start_time: new Date(Date.now() - 298700).toISOString(),
        end_time: new Date(Date.now() - 298500).toISOString(),
        duration_ms: 200,
        status: 'completed' as const,
        attributes: { output_length: 380 },
      },
    ],
    metadata: {
      user_id: 'user-12345',
      session_id: 'session-abc',
      environment: 'production',
    },
  }

  const displayTrace = trace ?? demoTrace
  const totalDuration = displayTrace.duration_ms ?? 0

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading trace...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/traces"
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5 text-gray-500" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{displayTrace.name}</h1>
            <StatusBadge status={displayTrace.status} />
          </div>
          <p className="text-sm text-gray-500 mt-1 font-mono">{displayTrace.trace_id}</p>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-50 rounded-lg">
              <CpuChipIcon className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Agent</p>
              <p className="text-sm font-medium text-gray-900">{displayTrace.agent_id}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <ClockIcon className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Duration</p>
              <p className="text-sm font-medium text-gray-900">
                {formatDuration(displayTrace.duration_ms ?? 0)}
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div>
            <p className="text-xs text-gray-500">Started</p>
            <p className="text-sm font-medium text-gray-900">
              {formatDate(displayTrace.start_time)}
            </p>
          </div>
        </Card>
        <Card className="p-4">
          <div>
            <p className="text-xs text-gray-500">Spans</p>
            <p className="text-sm font-medium text-gray-900">{displayTrace.spans.length}</p>
          </div>
        </Card>
      </div>

      {/* Timeline View */}
      <Card>
        <CardHeader title="Trace Timeline" subtitle="Visual representation of span execution" />
        <div className="space-y-2">
          {displayTrace.spans.map((span) => (
            <SpanRow key={span.span_id} span={span} totalDuration={totalDuration} />
          ))}
        </div>
      </Card>

      {/* Span Details */}
      <Card>
        <CardHeader title="Span Details" subtitle="Detailed information for each span" />
        <div className="divide-y divide-gray-200">
          {displayTrace.spans.map((span) => (
            <SpanDetails key={span.span_id} span={span} />
          ))}
        </div>
      </Card>

      {/* Metadata */}
      {displayTrace.metadata && (
        <Card>
          <CardHeader title="Metadata" subtitle="Additional trace context" />
          <pre className="text-sm text-gray-600 bg-gray-50 p-4 rounded-lg overflow-x-auto">
            {JSON.stringify(displayTrace.metadata, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  )
}

function SpanRow({ span, totalDuration }: { span: Span; totalDuration: number }) {
  const spanDuration = span.duration_ms ?? 0
  const widthPercent = totalDuration > 0 ? (spanDuration / totalDuration) * 100 : 0

  const typeColors: Record<string, string> = {
    execution: 'bg-blue-500',
    llm: 'bg-purple-500',
    tool: 'bg-green-500',
    mcp: 'bg-orange-500',
  }

  return (
    <div className="flex items-center gap-4 py-2">
      <div className="w-48 flex-shrink-0">
        <p className="text-sm font-medium text-gray-900 truncate">{span.name}</p>
        <p className="text-xs text-gray-500">{span.span_type}</p>
      </div>
      <div className="flex-1 h-6 bg-gray-100 rounded relative">
        <div
          className={cn('h-full rounded', typeColors[span.span_type] ?? 'bg-gray-400')}
          style={{ width: `${Math.max(widthPercent, 2)}%` }}
        />
      </div>
      <div className="w-20 text-right text-sm text-gray-600">
        {formatDuration(spanDuration)}
      </div>
    </div>
  )
}

function SpanDetails({ span }: { span: Span }) {
  const typeColors: Record<string, string> = {
    execution: 'text-blue-600 bg-blue-100',
    llm: 'text-purple-600 bg-purple-100',
    tool: 'text-green-600 bg-green-100',
    mcp: 'text-orange-600 bg-orange-100',
  }

  return (
    <div className="py-4">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium text-gray-900">{span.name}</h4>
            <span className={cn('badge', typeColors[span.span_type] ?? 'bg-gray-100 text-gray-600')}>
              {span.span_type}
            </span>
            <StatusBadge status={span.status} />
          </div>
          <p className="text-xs text-gray-500 font-mono mt-1">{span.span_id}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900">
            {formatDuration(span.duration_ms ?? 0)}
          </p>
          <p className="text-xs text-gray-500">{formatDate(span.start_time, 'HH:mm:ss.SSS')}</p>
        </div>
      </div>
      {span.attributes && Object.keys(span.attributes).length > 0 && (
        <div className="mt-2 bg-gray-50 rounded-lg p-3">
          <p className="text-xs font-medium text-gray-500 mb-2">Attributes</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(span.attributes).map(([key, value]) => (
              <div key={key}>
                <p className="text-xs text-gray-500">{key}</p>
                <p className="text-sm text-gray-900">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
