import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.database import init_db, DB_PATH
from backend.data.sp100 import SP100, SP100_TICKERS
from backend.models import WatchlistUpdate, AgentEvent
from backend.services import finnhub, portfolio as portfolio_svc
from backend.agents import researcher, trader
from backend import scheduler as sched_module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()
INTERVAL = int(os.getenv("AGENT_INTERVAL_MINUTES", "15"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    sched_module.set_broadcast(manager.broadcast)
    scheduler = sched_module.create_scheduler(INTERVAL)
    scheduler.start()
    logger.info(f"Scheduler started — agent cycle every {INTERVAL} min, price updates every 30s")
    yield
    scheduler.shutdown()


app = FastAPI(title="Autonomous Trader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── S&P 100 ──────────────────────────────────────────────────────────────────

@app.get("/sp100")
async def get_sp100():
    return {"stocks": SP100}


# ── Watchlist ────────────────────────────────────────────────────────────────

@app.get("/watchlist")
async def get_watchlist():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticker FROM watchlist") as cur:
            rows = await cur.fetchall()
    return {"tickers": [r[0] for r in rows]}


@app.post("/watchlist")
async def set_watchlist(body: WatchlistUpdate):
    invalid = [t for t in body.tickers if t not in SP100_TICKERS]
    if invalid:
        raise HTTPException(400, f"Unknown tickers: {invalid}")
    if len(body.tickers) > 10:
        raise HTTPException(400, "Maximum 10 tickers in watchlist")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM watchlist")
        for ticker in body.tickers:
            await db.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker,))
        await db.commit()
    return {"tickers": body.tickers}


# ── Portfolio ────────────────────────────────────────────────────────────────

@app.get("/portfolio")
async def get_portfolio():
    portfolio = await portfolio_svc.get_portfolio()
    return portfolio.model_dump()


@app.get("/trades")
async def get_trades(limit: int = 50):
    trades = await portfolio_svc.get_trades(limit)
    return {"trades": [t.model_dump() for t in trades]}


# ── Prices ───────────────────────────────────────────────────────────────────

@app.get("/prices/{ticker}")
async def get_price_history(ticker: str, resolution: str = "5"):
    if ticker not in SP100_TICKERS:
        raise HTTPException(400, f"Ticker {ticker} not in S&P 100")
    candles = await finnhub.get_candles(ticker, resolution=resolution)
    return {"ticker": ticker, "candles": candles}


@app.get("/quote/{ticker}")
async def get_quote(ticker: str):
    if ticker not in SP100_TICKERS:
        raise HTTPException(400, f"Ticker {ticker} not in S&P 100")
    quote = await finnhub.get_quote(ticker)
    return quote


# ── Agent trigger ────────────────────────────────────────────────────────────

@app.post("/agent/run")
async def trigger_agent_run(tickers: list[str] | None = None):
    """Manually trigger the agent cycle. Optionally specify tickers; defaults to full watchlist."""
    if tickers:
        invalid = [t for t in tickers if t not in SP100_TICKERS]
        if invalid:
            raise HTTPException(400, f"Unknown tickers: {invalid}")
        targets = tickers
    else:
        targets = await sched_module.get_watchlist()

    if not targets:
        raise HTTPException(400, "Watchlist is empty. Add tickers first.")

    # Run in background so API returns immediately
    asyncio.create_task(_run_agents_background(targets))
    return {"message": f"Agent cycle started for: {targets}"}


async def _run_agents_background(tickers: list[str]):
    for ticker in tickers:
        await sched_module.run_agent_cycle_for_ticker(ticker)
        await asyncio.sleep(1)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
