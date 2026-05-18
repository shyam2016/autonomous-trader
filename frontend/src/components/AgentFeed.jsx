import { useRef, useEffect } from 'react'

const S = {
  wrap: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', height: 400 },
  h: { fontSize: 14, fontWeight: 600, color: '#8b949e', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1, flexShrink: 0 },
  feed: { overflowY: 'auto', flex: 1 },
  event: (type) => ({
    borderLeft: `3px solid ${type === 'trade' ? actionColor : type === 'research' ? '#58a6ff' : type === 'error' ? '#f85149' : '#484f58'}`,
    padding: '10px 12px', marginBottom: 8, background: '#0d1117', borderRadius: '0 6px 6px 0', fontSize: 13,
  }),
  ts: { fontSize: 11, color: '#484f58', marginBottom: 4 },
  ticker: { fontWeight: 700, color: '#e6edf3', marginRight: 6 },
  empty: { color: '#484f58', fontSize: 13, textAlign: 'center', marginTop: 40 },
}

function actionColor(action) {
  if (action === 'BUY') return '#3fb950'
  if (action === 'SELL') return '#f85149'
  return '#8b949e'
}

function EventItem({ event }) {
  const { type, ticker, data, timestamp } = event
  const ts = timestamp ? new Date(timestamp).toLocaleTimeString() : ''

  if (type === 'price') return null // Don't clutter feed with price ticks

  if (type === 'research') {
    const rec = data.recommendation || 'NEUTRAL'
    const recColor = rec === 'BULLISH' ? '#3fb950' : rec === 'BEARISH' ? '#f85149' : '#8b949e'
    return (
      <div style={S.event('research')}>
        <div style={S.ts}>{ts} · Researcher Agent</div>
        <div>
          <span style={S.ticker}>{ticker}</span>
          <span style={{ color: recColor, fontWeight: 600 }}>{rec}</span>
          <span style={{ color: '#8b949e' }}> · confidence {((data.confidence || 0) * 100).toFixed(0)}%</span>
        </div>
        {data.bull_thesis && <div style={{ color: '#8b949e', marginTop: 4, fontSize: 12 }}>📈 {data.bull_thesis}</div>}
        {data.bear_thesis && <div style={{ color: '#8b949e', marginTop: 2, fontSize: 12 }}>📉 {data.bear_thesis}</div>}
        {data.key_news?.[0] && <div style={{ color: '#484f58', marginTop: 4, fontSize: 11 }}>📰 {data.key_news[0]}</div>}
      </div>
    )
  }

  if (type === 'trade') {
    const action = data.action || 'HOLD'
    const color = actionColor(action)
    return (
      <div style={{ ...S.event('trade'), borderLeftColor: color }}>
        <div style={S.ts}>{ts} · Trader Agent</div>
        <div>
          <span style={S.ticker}>{ticker}</span>
          <span style={{ color, fontWeight: 700, fontSize: 15 }}>{action}</span>
          {data.quantity > 0 && <span style={{ color: '#8b949e' }}> {data.quantity} shares</span>}
        </div>
        {data.rationale && <div style={{ color: '#8b949e', marginTop: 4, fontSize: 12 }}>{data.rationale}</div>}
      </div>
    )
  }

  if (type === 'status') {
    return (
      <div style={S.event('status')}>
        <div style={S.ts}>{ts}</div>
        <div style={{ color: '#8b949e' }}>{data.message}</div>
      </div>
    )
  }

  if (type === 'error') {
    return (
      <div style={S.event('error')}>
        <div style={S.ts}>{ts} · Error {ticker ? `· ${ticker}` : ''}</div>
        <div style={{ color: '#f85149' }}>{data.message}</div>
      </div>
    )
  }

  return null
}

export default function AgentFeed({ events }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const visible = events.filter(e => e.type !== 'price')

  return (
    <div style={S.wrap}>
      <div style={S.h}>Agent Activity Feed</div>
      <div style={S.feed}>
        {visible.length === 0
          ? <div style={S.empty}>No agent activity yet. Save a watchlist and click "Run Agents Now".</div>
          : visible.map((e, i) => <EventItem key={i} event={e} />)
        }
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
