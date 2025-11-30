import { useEffect, useState } from 'react'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import { Box, Chip, Stack, Typography } from '@mui/material'

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}m ${seconds}s`
}

function NextTickCounter({ nextTickAt, intervalMinutes = 30 }) {
  const [remaining, setRemaining] = useState('--')

  useEffect(() => {
    const update = () => {
      if (!nextTickAt) {
        setRemaining('--')
        return
      }
      const diff = new Date(nextTickAt).getTime() - Date.now()
      setRemaining(formatDuration(diff))
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [nextTickAt])

  return (
    <Box sx={{ p: 2, borderRadius: 2, border: '1px dashed', borderColor: 'divider', bgcolor: 'background.paper' }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <AccessTimeIcon color="secondary" />
        <Stack>
          <Typography variant="overline" color="text.secondary">
            Next update in
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6">{remaining}</Typography>
            <Chip size="small" label={`${intervalMinutes} min cadence`} color="secondary" variant="outlined" />
          </Stack>
        </Stack>
      </Stack>
    </Box>
  )
}

export default NextTickCounter
