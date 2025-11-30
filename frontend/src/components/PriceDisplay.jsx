import { Card, CardContent, Stack, Typography } from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'

function PriceDisplay({ price, changePercent }) {
  const positive = changePercent >= 0
  const color = positive ? 'success.main' : 'error.main'
  const label = positive ? 'Up' : 'Down'

  return (
    <Card sx={{ mb: 3, boxShadow: 10, background: 'linear-gradient(135deg, #312e81 0%, #7c3aed 100%)' }}>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack spacing={0.5}>
            <Typography variant="overline" color="rgba(255,255,255,0.8)">
              Current Price
            </Typography>
            <Typography variant="h3" color="#fff" fontWeight={800}>
              ${price.toFixed(2)}
            </Typography>
            <Typography variant="body2" color="rgba(255,255,255,0.85)">
              Updated every 30 minutes from Twitch chat momentum.
            </Typography>
          </Stack>
          <Stack alignItems="flex-end">
            <TrendingUpIcon sx={{ color: '#fff', fontSize: 42, mb: 1 }} />
            <Typography variant="h6" sx={{ color }}>
              {label} {Math.abs(changePercent).toFixed(2)}%
            </Typography>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

export default PriceDisplay
