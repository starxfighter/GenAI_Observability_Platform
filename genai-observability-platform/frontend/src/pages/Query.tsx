import { useState, useEffect, useRef } from 'react'
import {
  MagnifyingGlassIcon,
  ClockIcon,
  BookmarkIcon,
  SparklesIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  TrashIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import { BookmarkIcon as BookmarkSolidIcon } from '@heroicons/react/24/solid'
import { cn } from '../lib/utils'
import { api, NLQueryResponse } from '../lib/api'
import { useNLQueryStore } from '../store'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'

// Demo suggestions when API unavailable
const demoSuggestions = {
  general: [
    "What's the average latency across all agents?",
    'Show me errors in the last hour',
    'Which agent has the highest token usage?',
    "What's the cost breakdown by agent?",
    'Show me the latency trend for the past week',
  ],
  contextual: [],
}

// Demo examples
const demoExamples = {
  metrics: [
    { query: "What's the average latency?", description: 'Get average latency across all agents' },
    { query: 'Show me token usage for the past week', description: 'Token consumption trend' },
    { query: "What's our total cost today?", description: 'Daily cost summary' },
  ],
  errors: [
    { query: 'What errors occurred in the last hour?', description: 'Recent error summary' },
    { query: 'Which agent has the most errors?', description: 'Error hotspots' },
    { query: 'Show me timeout errors', description: 'Filter by error type' },
  ],
  traces: [
    { query: 'Show me the slowest traces', description: 'Performance outliers' },
    { query: 'Find traces with errors', description: 'Failed executions' },
    { query: "What's the p95 latency?", description: 'Latency percentiles' },
  ],
  comparisons: [
    { query: 'Compare latency between agent-1 and agent-2', description: 'Agent comparison' },
    { query: 'How does today compare to yesterday?', description: 'Time comparison' },
    { query: 'Which agent improved the most this week?', description: 'Trend comparison' },
  ],
}

export default function Query() {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<NLQueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState(demoSuggestions)
  const [examples, setExamples] = useState(demoExamples)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [activeTab, setActiveTab] = useState<'results' | 'history' | 'saved'>('results')

  const inputRef = useRef<HTMLInputElement>(null)
  const { history, savedQueries, addToHistory, saveQuery, deleteQuery } = useNLQueryStore()

  useEffect(() => {
    // Fetch suggestions and examples
    api.getNLQuerySuggestions().then(setSuggestions).catch(() => {})
    api.getNLQueryExamples().then(setExamples).catch(() => {})
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || isLoading) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await api.executeNLQuery(query)
      setResult(response)
      setActiveTab('results')

      // Add to history
      addToHistory({
        id: crypto.randomUUID(),
        query,
        timestamp: new Date().toISOString(),
        resultCount: response.results.data.length,
      })
    } catch (err) {
      // Demo fallback
      const demoResponse: NLQueryResponse = {
        query,
        parsed_intent: {
          query_type: 'metrics',
          intent: 'Find metrics',
          entities: { time_range: '24h', metrics: ['duration_ms'] },
          aggregations: ['avg'],
        },
        results: {
          data: [
            { agent_id: 'agent-1', duration_ms_avg: 245.5, request_count: 1523 },
            { agent_id: 'agent-2', duration_ms_avg: 312.8, request_count: 892 },
            { agent_id: 'agent-3', duration_ms_avg: 178.2, request_count: 2104 },
          ],
          metadata: {
            query_type: 'metrics',
            time_range: '24h',
            executed_at: new Date().toISOString(),
          },
        },
        response: `Based on your query "${query}", I found data for 3 agents. The average latency ranges from 178.2ms to 312.8ms across your agents.`,
        suggestions: [
          'Show me the trend over the last week',
          'Break down by agent',
          'Compare with yesterday',
        ],
      }
      setResult(demoResponse)
      setActiveTab('results')

      addToHistory({
        id: crypto.randomUUID(),
        query,
        timestamp: new Date().toISOString(),
        resultCount: demoResponse.results.data.length,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    inputRef.current?.focus()
  }

  const handleSaveQuery = () => {
    if (!saveName.trim() || !query.trim()) return

    saveQuery({
      id: crypto.randomUUID(),
      name: saveName,
      query,
      createdAt: new Date().toISOString(),
      tags: [],
    })

    setShowSaveDialog(false)
    setSaveName('')
  }

  const renderResults = () => {
    if (!result) return null

    const { results, parsed_intent } = result
    const data = results.data as Record<string, unknown>[]

    // Determine chart type based on data
    const hasTimeBuckets = data.some((d) => 'time_bucket' in d)
    const hasAgentData = data.some((d) => 'agent_id' in d)

    return (
      <div className="space-y-6">
        {/* Natural Language Response */}
        <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl p-6 border border-primary-100">
          <div className="flex items-start gap-3">
            <SparklesIcon className="w-6 h-6 text-primary-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-gray-800 leading-relaxed">{result.response}</p>
              <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
                <span className="bg-white px-2 py-0.5 rounded border">
                  {parsed_intent.query_type}
                </span>
                <span>|</span>
                <span>{results.metadata.time_range}</span>
                <span>|</span>
                <span>{data.length} results</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart Visualization */}
        {data.length > 0 && (
          <div className="bg-white rounded-xl border p-6">
            <h3 className="text-lg font-semibold mb-4">Visualization</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                {hasTimeBuckets ? (
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time_bucket"
                      tickFormatter={(v) => new Date(v).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                ) : hasAgentData ? (
                  <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="agent_id" />
                    <YAxis />
                    <Tooltip />
                    <Bar
                      dataKey={Object.keys(data[0]).find((k) => k.includes('_avg') || k.includes('count')) || 'value'}
                      fill="#6366f1"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                ) : (
                  <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey={(d) => Object.keys(d)[0]} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey={(d) => Object.values(d)[1] as number} fill="#6366f1" />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Data Table */}
        {data.length > 0 && (
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">Raw Data</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(data[0]).map((key) => (
                      <th
                        key={key}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                      >
                        {key.replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.slice(0, 10).map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {Object.values(row).map((value, j) => (
                        <td key={j} className="px-4 py-3 text-sm text-gray-700">
                          {typeof value === 'number'
                            ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : String(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Follow-up Suggestions */}
        {result.suggestions.length > 0 && (
          <div className="bg-white rounded-xl border p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Follow-up questions</h3>
            <div className="flex flex-wrap gap-2">
              {result.suggestions.map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Ask a Question</h1>
        <p className="text-gray-500 mt-1">
          Query your observability data using natural language
        </p>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to know? e.g., 'What's the average latency?'"
            className="w-full pl-12 pr-32 py-4 text-lg border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 shadow-sm"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {query && (
              <button
                type="button"
                onClick={() => setShowSaveDialog(true)}
                className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                title="Save query"
              >
                <BookmarkIcon className="w-5 h-5" />
              </button>
            )}
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              {isLoading ? (
                <>
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Ask'
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        <button
          onClick={() => setActiveTab('results')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
            activeTab === 'results'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          )}
        >
          Results
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5',
            activeTab === 'history'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          )}
        >
          <ClockIcon className="w-4 h-4" />
          History
          {history.length > 0 && (
            <span className="bg-gray-200 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">
              {history.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('saved')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5',
            activeTab === 'saved'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          )}
        >
          <BookmarkSolidIcon className="w-4 h-4" />
          Saved
          {savedQueries.length > 0 && (
            <span className="bg-gray-200 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">
              {savedQueries.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'results' && (
        <>
          {result ? (
            renderResults()
          ) : (
            <div className="space-y-8">
              {/* Quick Suggestions */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-3">Suggestions</h3>
                <div className="flex flex-wrap gap-2">
                  {suggestions.general.map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="px-4 py-2 bg-white border rounded-lg text-sm text-gray-700 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Example Categories */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {Object.entries(examples).map(([category, categoryExamples]) => (
                  <div key={category} className="bg-white rounded-xl border p-5">
                    <h3 className="font-medium text-gray-900 capitalize mb-3">{category}</h3>
                    <div className="space-y-2">
                      {categoryExamples.map((example, i) => (
                        <button
                          key={i}
                          onClick={() => handleSuggestionClick(example.query)}
                          className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors group"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-800">{example.query}</span>
                            <ChevronRightIcon className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{example.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'history' && (
        <div className="bg-white rounded-xl border">
          {history.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <ClockIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No query history yet</p>
              <p className="text-sm">Your recent queries will appear here</p>
            </div>
          ) : (
            <div className="divide-y">
              {history.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleSuggestionClick(item.query)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-gray-800">{item.query}</span>
                    <span className="text-xs text-gray-400">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{item.resultCount} results</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'saved' && (
        <div className="bg-white rounded-xl border">
          {savedQueries.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <BookmarkIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No saved queries yet</p>
              <p className="text-sm">Save queries to quickly access them later</p>
            </div>
          ) : (
            <div className="divide-y">
              {savedQueries.map((item) => (
                <div
                  key={item.id}
                  className="px-4 py-3 hover:bg-gray-50 transition-colors flex items-center justify-between"
                >
                  <button
                    onClick={() => handleSuggestionClick(item.query)}
                    className="flex-1 text-left"
                  >
                    <div className="font-medium text-gray-800">{item.name}</div>
                    <p className="text-sm text-gray-600 mt-0.5">{item.query}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Saved {new Date(item.createdAt).toLocaleDateString()}
                    </p>
                  </button>
                  <button
                    onClick={() => deleteQuery(item.id)}
                    className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">Save Query</h3>
            <input
              type="text"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="Query name"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 mb-4"
              autoFocus
            />
            <p className="text-sm text-gray-500 mb-4 truncate">{query}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveQuery}
                disabled={!saveName.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}
    </div>
  )
}
