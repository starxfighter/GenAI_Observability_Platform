import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { format, parseISO } from 'date-fns'

interface ChartData {
  timestamp: string
  value: number
  [key: string]: string | number
}

interface BaseChartProps {
  data: ChartData[]
  height?: number
  loading?: boolean
}

interface LineChartProps extends BaseChartProps {
  lines?: { key: string; color: string; name: string }[]
}

interface AreaChartProps extends BaseChartProps {
  color?: string
  fillOpacity?: number
}

interface BarChartProps extends BaseChartProps {
  color?: string
}

const formatXAxis = (timestamp: string) => {
  try {
    return format(parseISO(timestamp), 'HH:mm')
  } catch {
    return timestamp
  }
}

const formatTooltipLabel = (timestamp: string) => {
  try {
    return format(parseISO(timestamp), 'PPp')
  } catch {
    return timestamp
  }
}

export function MetricLineChart({
  data,
  height = 300,
  lines = [{ key: 'value', color: '#3b82f6', name: 'Value' }],
  loading,
}: LineChartProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="animate-pulse text-gray-400">Loading chart...</div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400" style={{ height }}>
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatXAxis}
          stroke="#9ca3af"
          fontSize={12}
        />
        <YAxis stroke="#9ca3af" fontSize={12} />
        <Tooltip
          labelFormatter={formatTooltipLabel}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Legend />
        {lines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name}
            stroke={line.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function MetricAreaChart({
  data,
  height = 300,
  color = '#3b82f6',
  fillOpacity = 0.3,
  loading,
}: AreaChartProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="animate-pulse text-gray-400">Loading chart...</div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400" style={{ height }}>
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatXAxis}
          stroke="#9ca3af"
          fontSize={12}
        />
        <YAxis stroke="#9ca3af" fontSize={12} />
        <Tooltip
          labelFormatter={formatTooltipLabel}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          fill={color}
          fillOpacity={fillOpacity}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function MetricBarChart({
  data,
  height = 300,
  color = '#3b82f6',
  loading,
}: BarChartProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="animate-pulse text-gray-400">Loading chart...</div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400" style={{ height }}>
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatXAxis}
          stroke="#9ca3af"
          fontSize={12}
        />
        <YAxis stroke="#9ca3af" fontSize={12} />
        <Tooltip
          labelFormatter={formatTooltipLabel}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
