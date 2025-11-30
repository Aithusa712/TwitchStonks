import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

function StonksChart({ data }) {
  const formatted = data.map((point) => ({
    ...point,
    timeLabel: point.timestamp instanceof Date ? point.timestamp.toLocaleTimeString() : point.timestamp,
  }))

  return (
    <div style={{ width: '100%', height: 400 }}>
      <ResponsiveContainer>
        <LineChart data={formatted} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timeLabel" tick={{ fontSize: 12 }} />
          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default StonksChart
