# Autonomous AI Trader

A production-grade, multi-agent paper trading web app powered by Claude AI. Two autonomous agents collaborate — a **Researcher Agent** that reads the market (news, sentiment, fundamentals) and a **Trader Agent** that makes buy/sell decisions — all running against a **$100,000 virtual portfolio** with real S&P 100 data.

> Built as a showcase of agentic AI systems using the Anthropic Claude API, FastAPI, and React.

---

## Live Demo

> Deployed at: `https://autonomous-trader.onrender.com` _(update after deploy)_

---

## What It Does

| Feature | Detail |
|---|---|
| Real-time prices | Finnhub API — quotes refreshed every 30 seconds |
| Researcher Agent | Claude reads news, sentiment, and financials → produces BULLISH / BEARISH / NEUTRAL report |
| Trader Agent | Claude reads the research + portfolio state → decides BUY / SELL / HOLD |
| Paper trading | $100k virtual portfolio with P&L tracking, no real money |
| Auto-cycle | Agents run every 15 min during market hours (9:30 AM–4 PM ET, Mon–Fri) |
| Live dashboard | React + Chart.js, WebSocket-powered, dark-mode UI |
| Stock universe | Top 100 S&P 500 stocks, user picks up to 10 to watch |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│                        (Vite + Chart.js)                        │
│                                                                 │
│   Watchlist Picker  │  Live Price Chart  │  Agent Activity Feed │
│   Portfolio P&L     │  Trade History     │  Connection Status   │
└────────────┬────────────────────────────────────────────────────┘
             │  REST API  +  WebSocket (/ws)
┌────────────▼────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                     │
│                                                                 │
│  REST Endpoints          WebSocket Manager       APScheduler    │
│  /sp100  /watchlist  →   broadcast to all   ←   every 15 min   │
│  /portfolio /trades      connected clients       + 30s prices   │
│  /agent/run (manual)                                            │
└────────┬──────────────────────────┬─────────────────────────────┘
         │                          │
┌────────▼──────────┐    ┌──────────▼──────────┐
│  Researcher Agent │    │    Trader Agent      │
│  (Claude claude-sonnet-4-6)  │    │  (Claude claude-sonnet-4-6)   │
│                   │    │                     │
│  Tools:           │    │  Tools:             │
│  get_stock_quote  │───▶│  get_portfolio      │
│  get_company_news │    │  get_position       │
│  get_sentiment    │    │  get_max_buy_qty    │
│  get_financials   │    │  buy_stock          │
│                   │    │  sell_stock         │
│  Output:          │    │                     │
│  Research Report  │    │  Output:            │
│  (JSON)           │    │  BUY / SELL / HOLD  │
└────────┬──────────┘    └──────────┬──────────┘
         │                          │
┌────────▼──────────────────────────▼─────────────────────────────┐
│                        Data Layer                                │
│                                                                 │
│   Finnhub API (free)        SQLite Database                     │
│   ─ Real-time quotes        ─ portfolio (cash)                  │
│   ─ Company news            ─ positions (ticker, qty, avg_cost) │
│   ─ News sentiment          ─ trades (full history)             │
│   ─ Fundamentals            ─ watchlist (active tickers)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
| Tool | Purpose |
|---|---|
| **Python 3.11** | Runtime |
| **FastAPI** | Async REST API + WebSocket server |
| **Anthropic SDK** | Claude claude-sonnet-4-6 agent calls with tool use |
| **APScheduler** | Background scheduler (price ticks + agent cycles) |
| **aiosqlite** | Async SQLite for portfolio/trade persistence |
| **httpx** | Async HTTP client for Finnhub API calls |
| **python-dotenv** | Environment variable management |
| **uvicorn** | ASGI server |

### Frontend
| Tool | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool + dev server |
| **Chart.js + react-chartjs-2** | Real-time price line charts |
| **WebSocket (native)** | Live event streaming from backend |

### External APIs
| API | What it provides | Cost |
|---|---|---|
| **Finnhub** | Real-time quotes, company news, sentiment scores, fundamentals | Free (60 req/min) |
| **Anthropic Claude** | AI reasoning for both agents | Pay-per-use |

---

## Design Patterns

### 1. Multi-Agent Pipeline
Two specialized Claude agents operate in sequence per ticker:
- **Researcher Agent** → gathers data via tools → returns structured JSON report
- **Trader Agent** → reads research + portfolio state → executes paper trade

Each agent has its own system prompt, tool set, and responsibility boundary. They communicate via structured JSON, not free-form text.

### 2. Tool Use (Function Calling)
Both agents use Claude's native tool use. Instead of "knowing" stock prices, agents call real tools:
- `get_stock_quote(ticker)` → hits Finnhub API
- `buy_stock(ticker, qty, price)` → writes to SQLite

This makes agents grounded in real data rather than hallucinated facts.

### 3. Agentic Loop
Each agent runs an autonomous `while True` loop: call Claude → if `stop_reason == "tool_use"` → execute tools → append results → call Claude again. The loop exits when Claude sets `stop_reason == "end_turn"` and returns a JSON decision.

### 4. Event-Driven WebSocket Broadcasting
A single `ConnectionManager` maintains all open WebSocket connections. The scheduler pushes events (price ticks, research reports, trade decisions) to every connected client in real-time. The React frontend renders updates without polling.

### 5. Risk-Gated Paper Trading
The Trader Agent's system prompt encodes hard risk rules:
- Max **10% of portfolio** in any single position
- **Stop-loss at -8%** unrealized loss triggers forced sell
- Only buy on **BULLISH** research with **≥ 60% confidence**

These rules are enforced at the portfolio service layer too (Python-side guard), not just via prompt.

### 6. Separation of Concerns
```
agents/          ← AI reasoning only (no DB access)
services/        ← Data access (Finnhub, portfolio)
backend/main.py  ← HTTP/WebSocket transport only
scheduler.py     ← Orchestration (wires agents + broadcasting)
```

---

## System Flow

```
Every 30 seconds:
  Scheduler → get_quote(each watchlist ticker) → broadcast price event → React updates chart

Every 15 minutes (market hours only):
  For each ticker in watchlist:

  1. RESEARCHER AGENT
     Claude ← "Research AAPL"
     Claude → tool_call: get_stock_quote("AAPL")
              tool_call: get_company_news("AAPL")
              tool_call: get_news_sentiment("AAPL")
              tool_call: get_basic_financials("AAPL")
     Claude → returns JSON research report
     Broadcast → "research" event → Agent Feed updates

  2. TRADER AGENT
     Claude ← research report + "make a trading decision"
     Claude → tool_call: get_portfolio()
              tool_call: get_position("AAPL")
              tool_call: get_max_buy_quantity("AAPL", price)
              tool_call: buy_stock("AAPL", 5, 213.50) [if bullish]
     Claude → returns BUY / SELL / HOLD decision
     Broadcast → "trade" event → Agent Feed + Portfolio refresh

On manual trigger ("Run Agents Now"):
  Same cycle, fires immediately regardless of market hours
```

---

## Project Structure

```
trader/
├── backend/
│   ├── main.py              # FastAPI app — REST routes, WebSocket, lifespan
│   ├── scheduler.py         # APScheduler — price updates + agent cycles
│   ├── database.py          # SQLite schema init
│   ├── models.py            # Pydantic models (Trade, Position, Portfolio…)
│   ├── agents/
│   │   ├── researcher.py    # Researcher Agent — tools + agentic loop
│   │   └── trader.py        # Trader Agent — tools + agentic loop
│   ├── services/
│   │   ├── finnhub.py       # Finnhub API client (quote, news, sentiment)
│   │   └── portfolio.py     # Paper trading logic (buy, sell, P&L)
│   └── data/
│       └── sp100.py         # Top 100 S&P 500 tickers + names
├── frontend/
│   ├── src/
│   │   ├── App.jsx                      # Root layout + WebSocket wiring
│   │   ├── components/
│   │   │   ├── Watchlist.jsx            # Searchable S&P 100 picker
│   │   │   ├── PriceChart.jsx           # Live Chart.js line chart
│   │   │   ├── Portfolio.jsx            # Cash, positions, P&L table
│   │   │   ├── AgentFeed.jsx            # Live agent activity stream
│   │   │   └── TradeHistory.jsx         # Executed trades table
│   │   └── hooks/
│   │       └── useWebSocket.js          # WS connection + auto-reconnect
│   ├── vite.config.js
│   └── package.json
├── requirements.txt
├── .env.example
└── README.md
```

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Finnhub API key](https://finnhub.io/register)
- An [Anthropic API key](https://console.anthropic.com)

### Step 1 — Clone and configure
```bash
git clone <your-repo-url>
cd trader
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=your_finnhub_key
PAPER_TRADING_CASH=100000
AGENT_INTERVAL_MINUTES=15
```

### Step 2 — Backend setup
```bash
# Create virtual environment (must use Python 3.11+)
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Step 3 — Frontend setup
```bash
cd frontend
npm install
cd ..
```

### Step 4 — Start the app

**Terminal 1 — Backend:**
```bash
./venv/bin/uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**

### Step 5 — Use the app
1. Search and select up to 10 tickers from the S&P 100 searchable dropdown
2. Click **Save Watchlist**
3. Click **▶ Run Agents Now** to trigger immediate AI analysis
4. Watch the **Agent Activity Feed** — research reports appear first, then trading decisions
5. Check the **Portfolio** panel for open positions and P&L
6. **Trade History** shows every executed paper trade

> The scheduler auto-runs agents every 15 minutes during market hours (9:30 AM – 4:00 PM ET, Mon–Fri) and refreshes prices every 30 seconds.

---

## Deploying to Render.com

This app deploys as **two separate Render services**: a Python Web Service (backend) and a Static Site (frontend).

### Prerequisites
- A [Render account](https://render.com) (free tier works)
- Your code pushed to a GitHub repository

---

### Part 1 — Deploy the Backend (Web Service)

1. Go to **Render Dashboard → New → Web Service**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---|---|
| **Name** | `autonomous-trader-api` |
| **Region** | Oregon (US West) or nearest |
| **Branch** | `main` |
| **Root Directory** | _(leave blank — repo root)_ |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free (or Starter for always-on) |

4. Under **Environment Variables**, add:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `FINNHUB_API_KEY` | `your_key` |
| `PAPER_TRADING_CASH` | `100000` |
| `AGENT_INTERVAL_MINUTES` | `15` |

5. Under **Advanced → Add Disk** (to persist the SQLite database across deploys):

| Setting | Value |
|---|---|
| **Name** | `trader-db` |
| **Mount Path** | `/data` |
| **Size** | 1 GB (free tier: not available — see note below) |

> **Note on SQLite persistence:** Render's free tier does not support persistent disks. The SQLite database (`trader.db`) resets on every deploy. For a persistent portfolio, either upgrade to Starter tier (which includes a disk) or switch to a free PostgreSQL database on Render (requires code change to use `asyncpg` instead of `aiosqlite`).

6. Update `backend/database.py` to use the mounted path on Render:

```python
import os
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "trader.db"))
```

Then add `DB_PATH=/data/trader.db` to Render environment variables when using the disk.

7. Click **Deploy** — Render will build and start the backend. Copy the URL (e.g. `https://autonomous-trader-api.onrender.com`).

---

### Part 2 — Deploy the Frontend (Static Site)

1. Go to **Render Dashboard → New → Static Site**
2. Connect the same GitHub repo
3. Configure:

| Setting | Value |
|---|---|
| **Name** | `autonomous-trader` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | `dist` |

4. Under **Environment Variables**, add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://autonomous-trader-api.onrender.com` |

5. Update `frontend/src/hooks/useWebSocket.js` to use the env var:

```js
const base = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`
const url = base.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws'
```

6. Update `frontend/src/components/*.jsx` API calls to use the env var:

```js
const API = import.meta.env.VITE_API_URL || ''
// then: fetch(`${API}/api/portfolio`)
```

7. Click **Deploy** — Render builds the React app and serves it as a CDN-backed static site.

---

### Part 3 — CORS Update

After deploying, add your frontend URL to the backend's CORS allowlist in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://autonomous-trader.onrender.com",  # your frontend URL
    ],
    ...
)
```

Redeploy the backend after this change.

---

### Render Free Tier Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| Spins down after 15 min inactivity | ~30s cold start on first visit | Upgrade to Starter ($7/mo) |
| No persistent disk | Portfolio resets on redeploy | Use Render PostgreSQL (free 1GB) |
| 750 hours/month compute | Enough for one always-on service | Keep backend on paid, frontend free |

---

### render.yaml (Infrastructure as Code)

Optionally, add this file to your repo root to configure both services automatically:

```yaml
services:
  - type: web
    name: autonomous-trader-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: FINNHUB_API_KEY
        sync: false
      - key: PAPER_TRADING_CASH
        value: "100000"
      - key: AGENT_INTERVAL_MINUTES
        value: "15"
    disk:
      name: trader-db
      mountPath: /data
      sizeGB: 1

  - type: web
    name: autonomous-trader
    runtime: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: ./dist
    envVars:
      - key: VITE_API_URL
        value: https://autonomous-trader-api.onrender.com
```

---

## Adding to Your Portfolio (shyamjain.com)

To embed this as a card on your portfolio site, use the following details:

```
Title:   Autonomous AI Trader
Tag:     Agentic AI · Python · React
Summary: A multi-agent paper trading system where a Researcher Agent
         (Claude AI) analyzes news and sentiment for S&P 100 stocks
         and a Trader Agent autonomously executes buy/sell decisions
         against a $100k virtual portfolio.
Stack:   FastAPI · Claude claude-sonnet-4-6 · React · Finnhub API · SQLite
Link:    https://autonomous-trader.onrender.com
GitHub:  https://github.com/yourusername/autonomous-trader
```

**Suggested card screenshot areas to highlight:**
- Agent Activity Feed (shows AI reasoning in real-time)
- Live price chart with trade markers
- Portfolio P&L breakdown

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `FINNHUB_API_KEY` | Yes | — | Finnhub API key (free tier) |
| `PAPER_TRADING_CASH` | No | `100000` | Starting virtual cash |
| `AGENT_INTERVAL_MINUTES` | No | `15` | How often agents run (minutes) |
| `DB_PATH` | No | `./backend/trader.db` | SQLite file path (set to `/data/trader.db` on Render) |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/sp100` | Full list of S&P 100 tickers |
| GET | `/watchlist` | Get active watchlist |
| POST | `/watchlist` | Set watchlist `{"tickers": ["AAPL", "TSLA"]}` |
| GET | `/portfolio` | Current positions, cash, P&L |
| GET | `/trades` | Trade history (last 50) |
| GET | `/prices/{ticker}` | Intraday candles for chart |
| GET | `/quote/{ticker}` | Latest real-time quote |
| POST | `/agent/run` | Manually trigger agent cycle |
| WS | `/ws` | WebSocket — live price + agent events |

---

## License

MIT — free to use, fork, and showcase.
