import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline'
import { Table, Pagination, StatusBadge } from '../components'
import { TimeRangeSelector } from '../components/TimeRangeSelector'
import { useTraces } from '../lib/hooks'
import { formatRelativeTime, formatDuration, truncate } from '../lib/utils'
import { TimeRange, Trace, TraceFilters } from '../types'

export default function Traces() {
  const navigate = useNavigate()
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<TraceFilters>({})
  const [searchQuery, setSearchQuery] = useState('')

  const { data: traces, isLoading } = useTraces(filters, page, 20)

  const columns = [
    {
      key: 'trace_id',
      header: 'Trace ID',
      render: (trace: Trace) => (
        <span className="font-mono text-sm text-primary-600">{truncate(trace.trace_id, 12)}</span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (trace: Trace) => (
        <div>
          <p className="font-medium text-gray-900">{trace.name}</p>
          <p className="text-xs text-gray-500">{trace.agent_id}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (trace: Trace) => <StatusBadge status={trace.status} />,
    },
    {
      key: 'spans',
      header: 'Spans',
      render: (trace: Trace) => (
        <span className="text-gray-600">{trace.spans?.length ?? 0}</span>
      ),
    },
    {
      key: 'duration_ms',
      header: 'Duration',
      render: (trace: Trace) => (
        <span className="text-gray-600">
          {trace.duration_ms ? formatDuration(trace.duration_ms) : '-'}
        </span>
      ),
    },
    {
      key: 'start_time',
      header: 'Started',
      render: (trace: Trace) => (
        <span className="text-gray-500">{formatRelativeTime(trace.start_time)}</span>
      ),
    },
  ]

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ ...filters, agent_id: searchQuery || undefined })
    setPage(1)
  }

  // Demo data when API not available
  const demoTraces: Trace[] = [
    {
      trace_id: 'trace-abc123def456',
      agent_id: 'customer-support-bot',
      name: 'Customer inquiry processing',
      start_time: new Date(Date.now() - 300000).toISOString(),
      end_time: new Date(Date.now() - 298500).toISOString(),
      duration_ms: 1500,
      status: 'completed',
      spans: [{} as never, {} as never, {} as never],
    },
    {
      trace_id: 'trace-xyz789ghi012',
      agent_id: 'data-analysis-agent',
      name: 'Report generation',
      start_time: new Date(Date.now() - 600000).toISOString(),
      end_time: new Date(Date.now() - 595000).toISOString(),
      duration_ms: 5000,
      status: 'completed',
      spans: [{} as never, {} as never, {} as never, {} as never, {} as never],
    },
    {
      trace_id: 'trace-mno345pqr678',
      agent_id: 'content-generator',
      name: 'Blog post creation',
      start_time: new Date(Date.now() - 120000).toISOString(),
      duration_ms: undefined,
      status: 'running',
      spans: [{} as never, {} as never],
    },
    {
      trace_id: 'trace-stu901vwx234',
      agent_id: 'code-assistant',
      name: 'Code review analysis',
      start_time: new Date(Date.now() - 900000).toISOString(),
      end_time: new Date(Date.now() - 897000).toISOString(),
      duration_ms: 3000,
      status: 'error',
      spans: [{} as never, {} as never, {} as never],
    },
    {
      trace_id: 'trace-yza567bcd890',
      agent_id: 'research-agent',
      name: 'Market research compilation',
      start_time: new Date(Date.now() - 1800000).toISOString(),
      end_time: new Date(Date.now() - 1790000).toISOString(),
      duration_ms: 10000,
      status: 'completed',
      spans: [{} as never, {} as never, {} as never, {} as never, {} as never, {} as never, {} as never, {} as never],
    },
  ]

  const displayData = traces?.items ?? demoTraces

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Traces</h1>
          <p className="text-sm text-gray-500 mt-1">
            View and analyze execution traces from your agents
          </p>
        </div>
        <div className="w-48">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <form onSubmit={handleSearch} className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by agent ID or trace ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>
          <button type="submit" className="btn-primary">
            Search
          </button>
          <button type="button" className="btn-secondary flex items-center gap-2">
            <FunnelIcon className="w-4 h-4" />
            Filters
          </button>
        </form>
      </div>

      {/* Traces Table */}
      <Table
        columns={columns}
        data={displayData}
        loading={isLoading}
        keyExtractor={(trace) => trace.trace_id}
        onRowClick={(trace) => navigate(`/traces/${trace.trace_id}`)}
        emptyMessage="No traces found"
      />

      {/* Pagination */}
      {(traces?.total ?? displayData.length) > 20 && (
        <Pagination
          page={page}
          pageSize={20}
          total={traces?.total ?? displayData.length}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
