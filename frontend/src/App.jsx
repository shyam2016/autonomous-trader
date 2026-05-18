import { useState, useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import Watchlist from './components/Watchlist'
import PriceChart from './components/PriceChart'
import Portfolio from './components/Portfolio'
import AgentFeed from './components/AgentFeed'
import TradeHistory from './components/TradeHistory'

const S = {
  app: { minHeight: '100vh', background: '#0d1117', color: '#e6edf3' },
  header: { background: '#161b22', borderBottom: '1px solid #30363d', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 18, fontWeight: 700, color: '#e6edf3', display: 'flex', alignItems: 'center', gap: 8 },
  dot: (connected) => ({ width: 8, height: 8, borderRadius: '50%', background: connected ? '#3fb950' : '#f85149' }),
  connLabel: (connected) => ({ fontSize: 12, color: connected ? '#3fb950' : '#f85149' }),
  main: { padding: 20, maxWidth: 1400, margin: '0 auto' },
  grid: { display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16, marginBottom: 16 },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 },
  full: { marginBottom: 16 },
}

export default function App() {
  const [events, setEvents] = useState([])
  const [liveQuotes, setLiveQuotes] = useState({})
  const [watchlist, setWatchlist] = useState([])
  const [connected, setConnected] = useState(false)
  const [refreshTick, setRefreshTick] = useState(0)

  const onMessage = useCallback((msg) => {
    if (msg.type === 'pong') return
    if (msg.type === 'price') {
      setLiveQuotes(prev => ({ ...prev, [msg.ticker]: msg.data }))
      return
    }
    if (msg.type === 'trade' && msg.data?.action !== 'HOLD') {
      // Trigger portfolio/trade history refresh after a trade
      setRefreshTick(t => t + 1)
    }
    setEvents(prev => [...prev.slice(-200), { ...msg, _id: Date.now() + Math.random() }])
  }, [])

  // Patch useWebSocket to expose connection status
  const onMessageWithConn = useCallback((msg) => {
    setConnected(true)
    onMessage(msg)
  }, [onMessage])

  useWebSocket(onMessageWithConn)

  return (
    <div style={S.app}>
      <header style={S.header}>
        <div style={S.title}>
          <span>⚡</span> Autonomous Trader
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={S.dot(connected)} />
          <span style={S.connLabel(connected)}>{connected ? 'Live' : 'Connecting...'}</span>
        </div>
      </header>

      <main style={S.main}>
        <div style={S.grid}>
          <Watchlist onWatchlistChange={setWatchlist} />
          <PriceChart watchlist={watchlist} liveQuotes={liveQuotes} />
        </div>

        <div style={S.grid2}>
          <Portfolio refreshTick={refreshTick} />
          <AgentFeed events={events} />
        </div>

        <div style={S.full}>
          <TradeHistory refreshTick={refreshTick} />
        </div>
      </main>
    </div>
  )
}
