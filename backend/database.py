import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "trader.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cash REAL NOT NULL DEFAULT 100000.0
);

CREATE TABLE IF NOT EXISTS positions (
    ticker TEXT PRIMARY KEY,
    qty REAL NOT NULL,
    avg_cost REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ticker TEXT NOT NULL,
    action TEXT NOT NULL,
    qty REAL NOT NULL,
    price REAL NOT NULL,
    total REAL NOT NULL,
    realized_pnl REAL,
    rationale TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    PRIMARY KEY (ticker, timestamp)
);
"""

INITIAL_CASH = float(os.getenv("PAPER_TRADING_CASH", "100000"))


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        # Seed portfolio row if not exists
        await db.execute(
            "INSERT OR IGNORE INTO portfolio (id, cash) VALUES (1, ?)", (INITIAL_CASH,)
        )
        await db.commit()


def get_db_path() -> str:
    return DB_PATH
