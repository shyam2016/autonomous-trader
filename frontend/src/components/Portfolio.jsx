import { useEffect, useState } from 'react'

const S = {
  wrap: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16 },
  h: { fontSize: 14, fontWeight: 600, color: '#8b949e', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 },
  stats: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 },
  stat: { background: '#0d1117', borderRadius: 6, padding: 12 },
  label: { fontSize: 11, color: '#8b949e', marginBottom: 4, textTransform: 'uppercase' },
  value: (color) => ({ fontSize: 18, fontWeight: 700, color: color || '#e6edf3' }),
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', color: '#8b949e', fontSize: 11, padding: '6px 8px', borderBottom: '1px solid #21262d', textTransform: 'uppercase' },
  td: { padding: '8px', borderBottom: '1px solid #21262d' },
  pnl: (v) => ({ color: v >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }),
}

function fmt(n) { return n?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }

export default function Portfolio({ refreshTick }) {
  const [data, setData] = useState(null)

  const load = () => fetch('/api/portfolio').then(r => r.json()).then(setData)

  useEffect(() => { load() }, [refreshTick])

  if (!data) return <div style={S.wrap}><div style={S.h}>Portfolio</div><p style={{ color: '#8b949e' }}>Loading...</p></div>

  return (
    <div style={S.wrap}>
      <div style={S.h}>Paper Portfolio</div>
      <div style={S.stats}>
        <div style={S.stat}>
          <div style={S.label}>Total Value</div>
          <div style={S.value()}>${fmt(data.total_value)}</div>
        </div>
        <div style={S.stat}>
          <div style={S.label}>Cash</div>
          <div style={S.value('#58a6ff')}>${fmt(data.cash)}</div>
        </div>
        <div style={S.stat}>
          <div style={S.label}>Total P&L</div>
          <div style={S.value(data.total_pnl >= 0 ? '#3fb950' : '#f85149')}>
            {data.total_pnl >= 0 ? '+' : ''}${fmt(data.total_pnl)}
            <span style={{ fontSize: 12, marginLeft: 4 }}>({data.total_pnl_pct?.toFixed(2)}%)</span>
          </div>
        </div>
      </div>

      {data.positions?.length > 0 ? (
        <table style={S.table}>
          <thead>
            <tr>
              {['Ticker', 'Qty', 'Avg Cost', 'Mkt Value', 'Unrealized P&L'].map(h =>
                <th key={h} style={S.th}>{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {data.positions.map(p => (
              <tr key={p.ticker}>
                <td style={{ ...S.td, fontWeight: 700 }}>{p.ticker}</td>
                <td style={S.td}>{p.qty}</td>
                <td style={S.td}>${fmt(p.avg_cost)}</td>
                <td style={S.td}>${fmt(p.market_value || p.qty * p.avg_cost)}</td>
                <td style={S.td}>
                  <span style={S.pnl(p.unrealized_pnl)}>
                    {p.unrealized_pnl >= 0 ? '+' : ''}${fmt(p.unrealized_pnl)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#8b949e', fontSize: 13, textAlign: 'center', padding: 16 }}>
          No open positions. Run agents to start trading.
        </p>
      )}
    </div>
  )
}
