import { alpha, Box, LinearProgress, useTheme } from '@mui/material'
import { LineChart } from '@mui/x-charts/LineChart'

function StonksChart({ data, loading }) {
  const theme = useTheme()

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
            valueFormatter: (value) => new Date(value).toLocaleString(),
          },
        ]}
        yAxis={[{ label: 'Price' }]}
        series={[
          {
            dataKey: 'price',
            label: 'Price',
            color: theme.palette.primary.main,
            showMark: false,
          },
        ]}
        height={420}
        dataset={chartData}
        sx={{
          '& .MuiLineElement-root': {
            filter: 'drop-shadow(0px 8px 12px rgba(124, 58, 237, 0.35))',
          },
          '& .MuiAreaElement-root': {
            fill: alpha(theme.palette.primary.main, 0.06),
          },
        }}
      />
    </Box>
  )
}

export default StonksChart
