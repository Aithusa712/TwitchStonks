import { useEffect, useMemo, useState } from 'react'
import StonksChart from './components/StonksChart'
import './App.css'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [dataPoints, setDataPoints] = useState([])

  const wsUrl = useMemo(() => {
    if (apiBaseUrl.startsWith('https')) {
      return apiBaseUrl.replace('https', 'wss') + '/ws'
    }
    return apiBaseUrl.replace('http', 'ws') + '/ws'
  }, [])

  useEffect(() => {
    async function loadHistory() {
      try {
        const response = await fetch(`${apiBaseUrl}/history`)
        const data = await response.json()
        setDataPoints(data.map((d) => ({ ...d, timestamp: new Date(d.timestamp) })))
      } catch (error) {
        console.error('Failed to load history', error)
      }
    }
    loadHistory()
  }, [])

  useEffect(() => {
    const ws = new WebSocket(wsUrl)
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        setDataPoints((prev) => [...prev, { ...payload, timestamp: new Date(payload.timestamp) }])
      } catch (error) {
        console.error('Failed to parse websocket message', error)
      }
    }
    ws.onopen = () => console.log('Connected to websocket')
    ws.onerror = (err) => console.error('Websocket error', err)
    return () => ws.close()
  }, [wsUrl])

  return (
    <div className="app">
      <header>
        <h1>Twitch Stonks</h1>
        <p>Live price reacting to chat mentioning the keyword.</p>
      </header>
      <main>
        <StonksChart data={dataPoints} />
      </main>
    </div>
  )
}

export default App
