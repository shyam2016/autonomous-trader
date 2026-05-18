from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Position(BaseModel):
    ticker: str
    qty: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


class Trade(BaseModel):
    id: Optional[int] = None
    timestamp: str
    ticker: str
    action: str  # BUY | SELL
    qty: float
    price: float
    total: float
    realized_pnl: Optional[float] = None
    rationale: str = ""


class Portfolio(BaseModel):
    cash: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: list[Position]


class ResearchReport(BaseModel):
    ticker: str
    current_price: float
    sentiment_score: float
    key_news: list[str]
    bull_thesis: str
    bear_thesis: str
    recommendation: str  # BULLISH | BEARISH | NEUTRAL
    confidence: float
    timestamp: str


class TradeDecision(BaseModel):
    ticker: str
    action: str  # BUY | SELL | HOLD
    quantity: float
    rationale: str
    timestamp: str


class WatchlistUpdate(BaseModel):
    tickers: list[str]


class AgentEvent(BaseModel):
    type: str  # research | trade | price | error | status
    ticker: Optional[str] = None
    data: dict
    timestamp: str
