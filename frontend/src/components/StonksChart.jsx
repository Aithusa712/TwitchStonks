import { alpha, Box, LinearProgress, useTheme } from '@mui/material'
import { LineChart } from '@mui/x-charts/LineChart'

function StonksChart({ data, loading }) {
  const theme = useTheme()

  const formatTimestamp = (value) => {
    const date = new Date(value)
    const dayPart = new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
    }).format(date)
    const timePart = new Intl.DateTimeFormat('en', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(date)
    return `${dayPart}\n${timePart}`
  }

  const chartData = data.map((point) => ({
    ...point,
    timestamp: point.timestamp instanceof Date ? point.timestamp : new Date(point.timestamp),
  }))

  return (
    <Box sx={{ position: 'relative' }}>
      {loading && <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1 }} />}
      <LineChart
        xAxis={[
          {
            dataKey: 'timestamp',
            scaleType: 'time',
            valueFormatter: formatTimestamp,
            tickLabelStyle: {
              whiteSpace: 'pre-line',
              fontFamily: 'Roboto Mono, monospace',
              fontSize: 12,
            },
          },
        ]}
        yAxis={[
          {
            label: 'Price',
            labelOffset: 16,
            labelStyle: { fontWeight: 600, letterSpacing: 0.4 },
            tickLabelStyle: { fontFamily: 'Roboto Mono, monospace', fontSize: 12 },
          },
        ]}
        series={[
          {
            dataKey: 'price',
            label: 'Price',
            color: theme.palette.primary.main,
            showMark: false,
            area: true,
            curve: 'monotoneX',
          },
        ]}
        height={420}
        margin={{ top: 32, left: 80, right: 24, bottom: 48 }}
        dataset={chartData}
        sx={{
          '& .MuiLineElement-root': {
            filter: 'drop-shadow(0px 8px 12px rgba(124, 58, 237, 0.35))',
          },
          '& .MuiAreaElement-root': {
            fill: alpha(theme.palette.primary.main, 0.06),
          },
          '& .MuiChartsAxis-label': {
            fontWeight: 700,
            fontFamily: 'Roboto, sans-serif',
          },
          '& .MuiChartsLegend-root': {
            pb: 1,
          },
        }}
      />
    </Box>
  )
}

export default StonksChart
