import { useEffect, useState } from 'react'

const S = {
  wrap: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16 },
  h: { fontSize: 14, fontWeight: 600, color: '#8b949e', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', color: '#8b949e', fontSize: 11, padding: '6px 8px', borderBottom: '1px solid #21262d', textTransform: 'uppercase' },
  td: { padding: '8px', borderBottom: '1px solid #21262d' },
  badge: (action) => ({
    background: action === 'BUY' ? 'rgba(63,185,80,0.15)' : 'rgba(248,81,73,0.15)',
    color: action === 'BUY' ? '#3fb950' : '#f85149',
    borderRadius: 4, padding: '2px 8px', fontWeight: 700, fontSize: 12,
  }),
  pnl: (v) => ({ color: v > 0 ? '#3fb950' : v < 0 ? '#f85149' : '#8b949e', fontWeight: 600 }),
  empty: { color: '#8b949e', fontSize: 13, textAlign: 'center', padding: 24 },
}

function fmt(n) { return n?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }

export default function TradeHistory({ refreshTick }) {
  const [trades, setTrades] = useState([])

  const load = () => fetch('/api/trades?limit=30').then(r => r.json()).then(d => setTrades(d.trades || []))

  useEffect(() => { load() }, [refreshTick])

  return (
    <div style={S.wrap}>
      <div style={S.h}>Trade History</div>
      {trades.length === 0
        ? <div style={S.empty}>No trades executed yet.</div>
        : (
          <div style={{ overflowX: 'auto' }}>
            <table style={S.table}>
              <thead>
                <tr>
                  {['Time', 'Ticker', 'Action', 'Qty', 'Price', 'Total', 'Realized P&L'].map(h =>
                    <th key={h} style={S.th}>{h}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {trades.map(t => (
                  <tr key={t.id}>
                    <td style={{ ...S.td, color: '#8b949e', fontSize: 12 }}>
                      {new Date(t.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td style={{ ...S.td, fontWeight: 700 }}>{t.ticker}</td>
                    <td style={S.td}><span style={S.badge(t.action)}>{t.action}</span></td>
                    <td style={S.td}>{t.qty}</td>
                    <td style={S.td}>${fmt(t.price)}</td>
                    <td style={S.td}>${fmt(t.total)}</td>
                    <td style={S.td}>
                      {t.realized_pnl != null
                        ? <span style={S.pnl(t.realized_pnl)}>{t.realized_pnl >= 0 ? '+' : ''}${fmt(t.realized_pnl)}</span>
                        : <span style={{ color: '#484f58' }}>—</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }
    </div>
  )
}
