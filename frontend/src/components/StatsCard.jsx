import { Card, CardContent, Stack, Typography } from '@mui/material'

function StatsCard({ title, value, description, color = 'primary.main', icon }) {
  return (
    <Card sx={{ height: '100%', border: '1px solid', borderColor: 'divider', boxShadow: 6 }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={2}>
          {icon}
          <Stack spacing={0.5}>
            <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1 }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ color }}>
              {value}
            </Typography>
            {description && (
              <Typography variant="body2" color="text.secondary">
                {description}
              </Typography>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

export default StatsCard
