import { useEffect, useMemo, useState } from 'react'
import '@fontsource/roboto/300.css'
import '@fontsource/roboto/400.css'
import '@fontsource/roboto/500.css'
import '@fontsource/roboto/700.css'
import { AppBar, Box, Chip, Container, CssBaseline, Divider, Grid, IconButton, Skeleton, Stack, Toolbar, Tooltip, Typography } from '@mui/material'
import SignalCellularAltIcon from '@mui/icons-material/SignalCellularAlt'
import SportsEsportsIcon from '@mui/icons-material/SportsEsports'
import LiveTvIcon from '@mui/icons-material/LiveTv'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'

import StonksChart from './components/StonksChart'
import TimeRangeSelector from './components/TimeRangeSelector'
import StatsCard from './components/StatsCard'
import PriceDisplay from './components/PriceDisplay'
import NextTickCounter from './components/NextTickCounter'
import getTheme from './theme'
import { ThemeProvider } from '@mui/material/styles'
import './App.css'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || window.location.origin).replace(/\/$/, '')

function App() {
  const [dataPoints, setDataPoints] = useState([])
  const [selectedRange, setSelectedRange] = useState('3days')
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)
  const [twitchConnected, setTwitchConnected] = useState(false)
  const [streamLive, setStreamLive] = useState(false)
  const [twitchChannel, setTwitchChannel] = useState(
    import.meta.env.VITE_TWITCH_CHANNEL || ''
  )
  const [upKeyword, setUpKeyword] = useState('Up')
  const [downKeyword, setDownKeyword] = useState('Down')
  const [nextTickAt, setNextTickAt] = useState(null)
  const [tickIntervalMinutes, setTickIntervalMinutes] = useState(30)
  const [liveCounts, setLiveCounts] = useState({ up_count: 0, down_count: 0 })
  const [darkMode, setDarkMode] = useState(true)

  const wsUrl = useMemo(() => {
    if (apiBaseUrl.startsWith('https')) {
      return apiBaseUrl.replace('https', 'wss') + '/ws'
    }
    return apiBaseUrl.replace('http', 'ws') + '/ws'
  }, [apiBaseUrl])

  const loadHistory = async (range) => {
    setLoadingHistory(true)
    try {
      const response = await fetch(`${apiBaseUrl}/history?range=${range}`)
      const data = await response.json()
      setDataPoints(data.map((d) => ({ ...d, timestamp: new Date(d.timestamp) })))
    } catch (error) {
      console.error('Failed to load history', error)
    } finally {
      setLoadingHistory(false)
    }
  }

  const loadStatus = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/status`)
      const status = await response.json()
      setTwitchConnected(Boolean(status.twitch_connected))
      setStreamLive(Boolean(status.stream_live))
      setNextTickAt(status.next_tick_at ? new Date(status.next_tick_at) : null)
      if (status.twitch_channel) {
        setTwitchChannel(status.twitch_channel)
      }
      if (status.tick_interval_minutes) {
        setTickIntervalMinutes(status.tick_interval_minutes)
      }
      if (status.up_keyword) {
        setUpKeyword(status.up_keyword)
      }
      if (status.down_keyword) {
        setDownKeyword(status.down_keyword)
      }
    } catch (error) {
      console.error('Failed to load status', error)
    }
  }

  useEffect(() => {
    loadHistory(selectedRange)
  }, [selectedRange])

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => {
      setWsConnected(true)
    }
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.twitch_connected !== undefined) {
          setTwitchConnected(Boolean(payload.twitch_connected))
        }
        if (payload.stream_live !== undefined) {
          setStreamLive(Boolean(payload.stream_live))
        }
        if (payload.next_tick_at) {
          setNextTickAt(new Date(payload.next_tick_at))
        }
        if (payload.type === 'tick' && payload.timestamp) {
          const livePoint = { ...payload, timestamp: new Date(payload.timestamp) }
          setDataPoints((prev) => [...prev, livePoint])
        }
        if (payload.type === 'live_counts') {
          setLiveCounts({
            up_count: payload.up_count ?? 0,
            down_count: payload.down_count ?? 0,
          })
        }
      } catch (error) {
        console.error('Failed to parse websocket message', error)
      }
    }
    ws.onclose = () => setWsConnected(false)
    ws.onerror = () => setWsConnected(false)
    return () => ws.close()
  }, [wsUrl])

  const latest = dataPoints[dataPoints.length - 1]
  const previous = dataPoints[dataPoints.length - 2]
  const price = latest?.price ?? 0
  const changePercent = previous && previous.price
    ? ((price - previous.price) / previous.price) * 100
    : 0
  const upMentions = liveCounts.up_count ?? 0
  const downMentions = liveCounts.down_count ?? 0

  const background = darkMode
    ? 'linear-gradient(180deg, #0b1021 0%, #0f172a 60%, #0b1021 100%)'
    : 'linear-gradient(180deg, #f8fafc 0%, #e2e8f0 60%, #f8fafc 100%)'

  const muiTheme = useMemo(() => getTheme(darkMode ? 'dark' : 'light'), [darkMode])

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <Box className="app" sx={{ minHeight: '100vh', background }}>
        <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
          <Toolbar sx={{ justifyContent: 'space-between', gap: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <SignalCellularAltIcon color="primary" sx={{ fontSize: 36 }} />
              <Stack>
                <Typography variant="h5" fontWeight={800}>
                  Twitch Stonks
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Real-time chat sentiment powering a live stock price.
                </Typography>
              </Stack>
            </Stack>
            <Stack direction="row" spacing={2} alignItems="center">
              <Chip
                label={wsConnected ? 'WebSocket Live' : 'WebSocket Offline'}
                color={wsConnected ? 'success' : 'default'}
                variant={wsConnected ? 'filled' : 'outlined'}
              />
              <Chip
                label={twitchConnected ? 'Twitch Bot Connected' : 'Twitch Bot Offline'}
                color={twitchConnected ? 'success' : 'warning'}
                icon={<SportsEsportsIcon />}
                variant={twitchConnected ? 'filled' : 'outlined'}
              />
              <Chip
                label={streamLive ? 'Channel Live' : 'Channel Offline'}
                color={streamLive ? 'info' : 'default'}
                icon={<LiveTvIcon />}
                clickable={Boolean(twitchChannel)}
                component={twitchChannel ? 'a' : 'div'}
                href={twitchChannel ? `https://twitch.tv/${twitchChannel}` : undefined}
                target="_blank"
                rel="noopener noreferrer"
                variant={streamLive ? 'filled' : 'outlined'}
                
              />
              <Tooltip title="Toggle theme">
                <IconButton color="inherit" onClick={() => setDarkMode((prev) => !prev)}>
                  {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
                </IconButton>
              </Tooltip>
            </Stack>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ py: 4 }}>
          <PriceDisplay
            price={price}
            changePercent={changePercent}
            channelName={twitchChannel}
          />

          <Grid container spacing={3} sx={{ mb: 2 }}>
            <Grid item xs={12} md={3}>
              <StatsCard
                title={`${upKeyword} Mentions`}
                value={upMentions}
                description={`Current ${tickIntervalMinutes}-minute window`}
                color="success.main"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatsCard
                title={`${downKeyword} Mentions`}
                value={downMentions}
                description={`Current ${tickIntervalMinutes}-minute window`}
                color="error.main"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatsCard
                title="Price Change"
                value={`${price >= (previous?.price ?? price) ? '+' : '-'}${Math.abs(changePercent).toFixed(2)}%`}
                description="Since last tick"
                color={price >= (previous?.price ?? price) ? 'success.main' : 'error.main'}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <NextTickCounter nextTickAt={nextTickAt} intervalMinutes={tickIntervalMinutes} />
            </Grid>
          </Grid>

          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 2,
              flexWrap: 'wrap',
              gap: 2,
            }}
          >
            <Stack spacing={0.5}>
              <Typography variant="h5" fontWeight={700}>
                Price history
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Aggregated snapshots powered by MongoDB time-series data.
              </Typography>
            </Stack>
            <TimeRangeSelector value={selectedRange} onChange={setSelectedRange} />
          </Box>

          <Box sx={{ p: 3, borderRadius: 3, border: '1px solid', borderColor: 'divider', boxShadow: 4, bgcolor: 'background.paper' }}>
            {loadingHistory ? (
              <Stack spacing={2}>
                <Skeleton variant="rounded" height={48} />
                <Skeleton variant="rounded" height={400} />
              </Stack>
            ) : (
              <StonksChart data={dataPoints} loading={loadingHistory} />
            )}
          </Box>

          <Divider sx={{ my: 3, opacity: 0.4 }} />

          <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
            <Typography variant="body2">
              Listening for chat keywords every moment. Ticker executes independently every 30 minutes, even if Twitch is down.
            </Typography>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  )
}

export default App
