import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import aiosqlite

from backend.database import DB_PATH
from backend.agents import researcher, trader
from backend.services import finnhub

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
_broadcast_fn = None  # set by main.py


def set_broadcast(fn):
    global _broadcast_fn
    _broadcast_fn = fn


async def _broadcast(event: dict):
    if _broadcast_fn:
        await _broadcast_fn(event)


def _is_market_hours() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Saturday/Sunday
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


async def get_watchlist() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticker FROM watchlist") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def run_agent_cycle_for_ticker(ticker: str):
    """Run Researcher → Trader pipeline for one ticker and broadcast events."""
    try:
        # Broadcast research started
        await _broadcast({
            "type": "status",
            "ticker": ticker,
            "data": {"message": f"Researcher Agent analyzing {ticker}..."},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        report = await researcher.run(ticker)

        await _broadcast({
            "type": "research",
            "ticker": ticker,
            "data": report,
            "timestamp": report.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

        # Small delay between agents
        await asyncio.sleep(1)

        await _broadcast({
            "type": "status",
            "ticker": ticker,
            "data": {"message": f"Trader Agent making decision for {ticker}..."},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        decision = await trader.run(report)

        await _broadcast({
            "type": "trade",
            "ticker": ticker,
            "data": decision,
            "timestamp": decision.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

    except Exception as e:
        logger.error(f"Agent cycle error for {ticker}: {e}")
        await _broadcast({
            "type": "error",
            "ticker": ticker,
            "data": {"message": str(e)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


async def run_price_updates():
    """Push real-time price updates for all watchlist tickers."""
    tickers = await get_watchlist()
    for ticker in tickers:
        try:
            quote = await finnhub.get_quote(ticker)
            await _broadcast({
                "type": "price",
                "ticker": ticker,
                "data": quote,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await asyncio.sleep(0.5)  # avoid hitting rate limits
        except Exception as e:
            logger.warning(f"Price update failed for {ticker}: {e}")


async def run_full_agent_cycle():
    """Run agent cycle for all watched tickers (respects market hours)."""
    if not _is_market_hours():
        logger.info("Outside market hours — skipping agent cycle")
        await _broadcast({
            "type": "status",
            "ticker": None,
            "data": {"message": "Market is closed. Agents will resume during market hours (9:30 AM–4:00 PM ET)."},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return

    tickers = await get_watchlist()
    if not tickers:
        logger.info("Watchlist is empty — nothing to analyze")
        return

    logger.info(f"Starting agent cycle for: {tickers}")
    for ticker in tickers:
        await run_agent_cycle_for_ticker(ticker)
        await asyncio.sleep(2)  # brief pause between tickers


def create_scheduler(interval_minutes: int = 15) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Price updates every 30 seconds
    scheduler.add_job(
        run_price_updates,
        trigger=IntervalTrigger(seconds=30),
        id="price_updates",
        replace_existing=True,
    )

    # Agent cycle every N minutes
    scheduler.add_job(
        run_full_agent_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="agent_cycle",
        replace_existing=True,
    )

    return scheduler
