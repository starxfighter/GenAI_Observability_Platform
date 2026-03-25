import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MagnifyingGlassIcon, PlusIcon } from '@heroicons/react/24/outline'
import { Card, StatusBadge } from '../components'
import { useAgents } from '../lib/hooks'
import { formatRelativeTime, formatCompact } from '../lib/utils'
import { Agent } from '../types'

export default function Agents() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const { data: agents, isLoading } = useAgents(1, 50)

  // Demo data
  const demoAgents: Agent[] = [
    {
      agent_id: 'customer-support-bot',
      name: 'Customer Support Bot',
      framework: 'LangChain',
      version: '1.2.3',
      status: 'active',
      last_seen: new Date(Date.now() - 60000).toISOString(),
      created_at: new Date(Date.now() - 30 * 24 * 3600000).toISOString(),
      metadata: { environment: 'production', team: 'support' },
    },
    {
      agent_id: 'data-analysis-agent',
      name: 'Data Analysis Agent',
      framework: 'CrewAI',
      version: '2.0.1',
      status: 'active',
      last_seen: new Date(Date.now() - 120000).toISOString(),
      created_at: new Date(Date.now() - 60 * 24 * 3600000).toISOString(),
      metadata: { environment: 'production', team: 'analytics' },
    },
    {
      agent_id: 'content-generator',
      name: 'Content Generator',
      framework: 'LangChain',
      version: '1.5.0',
      status: 'active',
      last_seen: new Date(Date.now() - 300000).toISOString(),
      created_at: new Date(Date.now() - 45 * 24 * 3600000).toISOString(),
      metadata: { environment: 'production', team: 'marketing' },
    },
    {
      agent_id: 'code-assistant',
      name: 'Code Assistant',
      framework: 'Custom',
      version: '0.9.5',
      status: 'error',
      last_seen: new Date(Date.now() - 3600000).toISOString(),
      created_at: new Date(Date.now() - 15 * 24 * 3600000).toISOString(),
      metadata: { environment: 'staging', team: 'engineering' },
    },
    {
      agent_id: 'research-agent',
      name: 'Research Agent',
      framework: 'CrewAI',
      version: '1.1.0',
      status: 'inactive',
      last_seen: new Date(Date.now() - 86400000).toISOString(),
      created_at: new Date(Date.now() - 90 * 24 * 3600000).toISOString(),
      metadata: { environment: 'development', team: 'research' },
    },
  ]

  const displayAgents = agents?.items ?? demoAgents
  const filteredAgents = displayAgents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.agent_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading agents...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage and monitor your GenAI agents
          </p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <PlusIcon className="w-4 h-4" />
          Register Agent
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search agents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input pl-10"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Total Agents</p>
          <p className="text-2xl font-bold text-gray-900">{displayAgents.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Active</p>
          <p className="text-2xl font-bold text-green-600">
            {displayAgents.filter((a) => a.status === 'active').length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Inactive</p>
          <p className="text-2xl font-bold text-yellow-600">
            {displayAgents.filter((a) => a.status === 'inactive').length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Error</p>
          <p className="text-2xl font-bold text-red-600">
            {displayAgents.filter((a) => a.status === 'error').length}
          </p>
        </Card>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAgents.map((agent) => (
          <AgentCard
            key={agent.agent_id}
            agent={agent}
            onClick={() => navigate(`/agents/${agent.agent_id}`)}
          />
        ))}
        {filteredAgents.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            No agents found matching your search
          </div>
        )}
      </div>
    </div>
  )
}

function AgentCard({ agent, onClick }: { agent: Agent; onClick: () => void }) {
  // Demo metrics
  const metrics = {
    requests: Math.floor(Math.random() * 10000) + 1000,
    errorRate: Math.random() * 5,
    avgLatency: Math.floor(Math.random() * 500) + 100,
  }

  return (
    <Card
      className="p-5 cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
          <p className="text-sm text-gray-500 font-mono">{agent.agent_id}</p>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Framework</span>
          <span className="font-medium text-gray-900">{agent.framework}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Version</span>
          <span className="font-medium text-gray-900">{agent.version}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Last Seen</span>
          <span className="text-gray-600">{formatRelativeTime(agent.last_seen)}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-lg font-semibold text-gray-900">{formatCompact(metrics.requests)}</p>
            <p className="text-xs text-gray-500">Requests</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-900">{metrics.errorRate.toFixed(1)}%</p>
            <p className="text-xs text-gray-500">Error Rate</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-900">{metrics.avgLatency}ms</p>
            <p className="text-xs text-gray-500">Avg Latency</p>
          </div>
        </div>
      </div>
    </Card>
  )
}
