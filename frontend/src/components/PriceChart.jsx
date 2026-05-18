import { useEffect, useState, useRef } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const S = {
  wrap: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  ticker: { fontSize: 20, fontWeight: 700, color: '#e6edf3' },
  price: (chg) => ({ fontSize: 18, fontWeight: 600, color: chg >= 0 ? '#3fb950' : '#f85149' }),
  change: (chg) => ({ fontSize: 13, color: chg >= 0 ? '#3fb950' : '#f85149', marginLeft: 8 }),
  tabs: { display: 'flex', gap: 6, marginBottom: 12 },
  tab: (active) => ({ background: active ? '#1f6feb' : '#21262d', border: 'none', borderRadius: 6, padding: '4px 12px', color: active ? '#fff' : '#8b949e', cursor: 'pointer', fontSize: 12 }),
  empty: { height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e', fontSize: 13 },
}

const CHART_OPTIONS = {
  responsive: true, maintainAspectRatio: false, animation: false,
  plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
  scales: {
    x: { grid: { color: '#21262d' }, ticks: { color: '#8b949e', maxTicksLimit: 8, font: { size: 11 } } },
    y: { grid: { color: '#21262d' }, ticks: { color: '#8b949e', font: { size: 11 } } },
  },
}

export default function PriceChart({ watchlist, liveQuotes }) {
  const [activeTicker, setActiveTicker] = useState(null)
  const [candles, setCandles] = useState([])

  useEffect(() => {
    if (watchlist.length > 0 && !activeTicker) setActiveTicker(watchlist[0])
  }, [watchlist])

  useEffect(() => {
    if (!activeTicker) return
    setCandles([])
    fetch(`/api/prices/${activeTicker}?resolution=5`)
      .then(r => r.json())
      .then(d => setCandles(d.candles || []))
      .catch(() => {})
  }, [activeTicker])

  // Append live price ticks to chart
  useEffect(() => {
    if (!activeTicker || !liveQuotes[activeTicker]) return
    const q = liveQuotes[activeTicker]
    const now = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    setCandles(prev => {
      if (prev.length === 0) return [{ t: now, c: q.current }]
      const last = prev[prev.length - 1]
      if (last.t === now) {
        return [...prev.slice(0, -1), { ...last, c: q.current }]
      }
      const next = [...prev, { t: now, c: q.current }]
      return next.slice(-120) // keep last 120 data points
    })
  }, [liveQuotes, activeTicker])

  const quote = activeTicker ? liveQuotes[activeTicker] : null
  const chartData = {
    labels: candles.map(c => c.t),
    datasets: [{
      data: candles.map(c => c.c),
      borderColor: quote && quote.change_pct >= 0 ? '#3fb950' : '#f85149',
      backgroundColor: quote && quote.change_pct >= 0 ? 'rgba(63,185,80,0.08)' : 'rgba(248,81,73,0.08)',
      borderWidth: 2, pointRadius: 0, fill: true, tension: 0.2,
    }],
  }

  return (
    <div style={S.wrap}>
      <div style={S.tabs}>
        {watchlist.map(t => (
          <button key={t} style={S.tab(t === activeTicker)} onClick={() => setActiveTicker(t)}>{t}</button>
        ))}
      </div>
      {activeTicker && (
        <div style={S.header}>
          <span style={S.ticker}>{activeTicker}</span>
          {quote ? (
            <span>
              <span style={S.price(quote.change_pct)}>${quote.current?.toFixed(2)}</span>
              <span style={S.change(quote.change_pct)}>
                {quote.change_pct >= 0 ? '▲' : '▼'} {Math.abs(quote.change_pct)?.toFixed(2)}%
              </span>
            </span>
          ) : <span style={{ color: '#8b949e', fontSize: 13 }}>Loading...</span>}
        </div>
      )}
      <div style={{ height: 220 }}>
        {candles.length > 0
          ? <Line data={chartData} options={CHART_OPTIONS} />
          : <div style={S.empty}>{activeTicker ? 'Fetching price data...' : 'Select tickers from watchlist'}</div>
        }
      </div>
    </div>
  )
}
