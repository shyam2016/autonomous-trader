import { useState, useEffect, useRef } from 'react'

const S = {
  wrap: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16 },
  h: { fontSize: 14, fontWeight: 600, color: '#8b949e', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 },
  search: { width: '100%', background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: '8px 12px', color: '#e6edf3', fontSize: 14, marginBottom: 8, outline: 'none' },
  dropdown: { background: '#161b22', border: '1px solid #30363d', borderRadius: 6, maxHeight: 200, overflowY: 'auto', marginBottom: 12, position: 'absolute', zIndex: 100, width: '100%', left: 0 },
  dropItem: (selected) => ({ padding: '8px 12px', cursor: 'pointer', fontSize: 13, background: selected ? '#1f6feb22' : 'transparent', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }),
  chip: { display: 'inline-flex', alignItems: 'center', gap: 6, background: '#1f6feb33', border: '1px solid #1f6feb', borderRadius: 20, padding: '3px 10px', fontSize: 12, marginRight: 6, marginBottom: 6 },
  chipX: { cursor: 'pointer', color: '#8b949e', fontWeight: 700, fontSize: 14, lineHeight: 1 },
  btn: (disabled) => ({ background: disabled ? '#21262d' : '#238636', border: 'none', borderRadius: 6, padding: '8px 16px', color: disabled ? '#484f58' : '#fff', cursor: disabled ? 'not-allowed' : 'pointer', fontSize: 13, fontWeight: 600, marginTop: 8 }),
}

export default function Watchlist({ onWatchlistChange }) {
  const [sp100, setSp100] = useState([])
  const [selected, setSelected] = useState([])
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    fetch('/api/sp100').then(r => r.json()).then(d => setSp100(d.stocks))
    fetch('/api/watchlist').then(r => r.json()).then(d => setSelected(d.tickers || []))
  }, [])

  useEffect(() => {
    const handler = (e) => { if (!wrapRef.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = sp100.filter(s =>
    s.ticker.toLowerCase().includes(search.toLowerCase()) ||
    s.name.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 30)

  const toggle = (ticker) => {
    setSelected(prev =>
      prev.includes(ticker) ? prev.filter(t => t !== ticker) : prev.length < 10 ? [...prev, ticker] : prev
    )
  }

  const save = async () => {
    setSaving(true)
    await fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers: selected }),
    })
    setSaving(false)
    onWatchlistChange(selected)
  }

  const runAgents = async () => {
    setRunning(true)
    await fetch('/api/agent/run', { method: 'POST' })
    setRunning(false)
  }

  return (
    <div style={S.wrap}>
      <div style={S.h}>Watchlist (max 10)</div>
      <div style={{ position: 'relative' }} ref={wrapRef}>
        <input
          style={S.search}
          placeholder="Search S&P 100 tickers..."
          value={search}
          onChange={e => { setSearch(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
        />
        {open && filtered.length > 0 && (
          <div style={S.dropdown}>
            {filtered.map(s => (
              <div key={s.ticker} style={S.dropItem(selected.includes(s.ticker))} onClick={() => toggle(s.ticker)}>
                <span><b>{s.ticker}</b> <span style={{ color: '#8b949e' }}>{s.name}</span></span>
                {selected.includes(s.ticker) && <span style={{ color: '#3fb950' }}>✓</span>}
              </div>
            ))}
          </div>
        )}
      </div>
      <div style={{ minHeight: 36 }}>
        {selected.map(t => (
          <span key={t} style={S.chip}>
            {t}
            <span style={S.chipX} onClick={() => setSelected(prev => prev.filter(x => x !== t))}>×</span>
          </span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button style={S.btn(saving || selected.length === 0)} onClick={save} disabled={saving || selected.length === 0}>
          {saving ? 'Saving...' : 'Save Watchlist'}
        </button>
        <button
          style={{ ...S.btn(running || selected.length === 0), background: running || selected.length === 0 ? '#21262d' : '#1f6feb' }}
          onClick={runAgents}
          disabled={running || selected.length === 0}
        >
          {running ? 'Running...' : '▶ Run Agents Now'}
        </button>
      </div>
    </div>
  )
}
