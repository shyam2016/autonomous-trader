import aiosqlite
from datetime import datetime, timezone
from backend.database import DB_PATH
from backend.models import Position, Trade, Portfolio

MAX_POSITION_PCT = 0.10  # max 10% of portfolio in one stock
STOP_LOSS_PCT = -0.08    # auto-sell trigger at -8%


async def get_cash() -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT cash FROM portfolio WHERE id=1") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0


async def get_positions() -> list[Position]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticker, qty, avg_cost FROM positions") as cur:
            rows = await cur.fetchall()
    return [Position(ticker=r[0], qty=r[1], avg_cost=r[2]) for r in rows]


async def get_position(ticker: str) -> Position | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ticker, qty, avg_cost FROM positions WHERE ticker=?", (ticker,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return Position(ticker=row[0], qty=row[1], avg_cost=row[2])


async def get_portfolio(current_prices: dict[str, float] | None = None) -> Portfolio:
    cash = await get_cash()
    positions = await get_positions()
    cp = current_prices or {}
    total_market_value = cash
    for p in positions:
        price = cp.get(p.ticker, p.avg_cost)
        p.current_price = price
        p.market_value = p.qty * price
        p.unrealized_pnl = (price - p.avg_cost) * p.qty
        p.unrealized_pnl_pct = ((price - p.avg_cost) / p.avg_cost * 100) if p.avg_cost else 0
        total_market_value += p.market_value

    from backend.database import INITIAL_CASH
    total_pnl = total_market_value - INITIAL_CASH
    total_pnl_pct = (total_pnl / INITIAL_CASH * 100) if INITIAL_CASH else 0

    return Portfolio(
        cash=cash,
        total_value=total_market_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        positions=positions,
    )


async def buy(ticker: str, qty: float, price: float, rationale: str = "") -> Trade:
    total_cost = qty * price
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT cash FROM portfolio WHERE id=1") as cur:
            row = await cur.fetchone()
        cash = row[0] if row else 0.0
        if total_cost > cash:
            raise ValueError(f"Insufficient cash: need ${total_cost:.2f}, have ${cash:.2f}")

        # Update or insert position
        async with db.execute("SELECT qty, avg_cost FROM positions WHERE ticker=?", (ticker,)) as cur:
            pos = await cur.fetchone()
        if pos:
            new_qty = pos[0] + qty
            new_avg = (pos[0] * pos[1] + total_cost) / new_qty
            await db.execute(
                "UPDATE positions SET qty=?, avg_cost=? WHERE ticker=?", (new_qty, new_avg, ticker)
            )
        else:
            await db.execute(
                "INSERT INTO positions (ticker, qty, avg_cost) VALUES (?, ?, ?)",
                (ticker, qty, price),
            )

        await db.execute("UPDATE portfolio SET cash=cash-? WHERE id=1", (total_cost,))
        ts = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO trades (timestamp, ticker, action, qty, price, total, rationale) VALUES (?,?,?,?,?,?,?)",
            (ts, ticker, "BUY", qty, price, total_cost, rationale),
        )
        await db.commit()

    return Trade(
        timestamp=ts, ticker=ticker, action="BUY",
        qty=qty, price=price, total=total_cost, rationale=rationale,
    )


async def sell(ticker: str, qty: float, price: float, rationale: str = "") -> Trade:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT qty, avg_cost FROM positions WHERE ticker=?", (ticker,)) as cur:
            pos = await cur.fetchone()
        if not pos or pos[0] < qty:
            held = pos[0] if pos else 0
            raise ValueError(f"Cannot sell {qty} {ticker}: only holding {held}")

        avg_cost = pos[1]
        realized_pnl = (price - avg_cost) * qty
        total_proceeds = qty * price
        new_qty = pos[0] - qty

        if new_qty < 0.0001:
            await db.execute("DELETE FROM positions WHERE ticker=?", (ticker,))
        else:
            await db.execute("UPDATE positions SET qty=? WHERE ticker=?", (new_qty, ticker))

        await db.execute("UPDATE portfolio SET cash=cash+? WHERE id=1", (total_proceeds,))
        ts = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO trades (timestamp, ticker, action, qty, price, total, realized_pnl, rationale) VALUES (?,?,?,?,?,?,?,?)",
            (ts, ticker, "SELL", qty, price, total_proceeds, realized_pnl, rationale),
        )
        await db.commit()

    return Trade(
        timestamp=ts, ticker=ticker, action="SELL",
        qty=qty, price=price, total=total_proceeds,
        realized_pnl=realized_pnl, rationale=rationale,
    )


async def get_trades(limit: int = 50) -> list[Trade]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, timestamp, ticker, action, qty, price, total, realized_pnl, rationale FROM trades ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [
        Trade(id=r[0], timestamp=r[1], ticker=r[2], action=r[3],
              qty=r[4], price=r[5], total=r[6], realized_pnl=r[7], rationale=r[8])
        for r in rows
    ]


async def max_buy_quantity(ticker: str, price: float) -> float:
    """Returns how many shares we can buy within the 10% position limit."""
    portfolio = await get_portfolio({ticker: price})
    max_value = portfolio.total_value * MAX_POSITION_PCT
    existing_pos = await get_position(ticker)
    existing_value = (existing_pos.qty * price) if existing_pos else 0
    available_budget = min(portfolio.cash, max(0, max_value - existing_value))
    if price <= 0:
        return 0
    qty = available_budget / price
    return round(qty, 4)
