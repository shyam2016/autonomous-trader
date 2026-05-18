import httpx
import os
from datetime import datetime, timedelta
from typing import Optional

FINNHUB_BASE = "https://finnhub.io/api/v1"


def _api_key() -> str:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        raise ValueError("FINNHUB_API_KEY not set in environment")
    return key


async def get_quote(ticker: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{FINNHUB_BASE}/quote",
            params={"symbol": ticker, "token": _api_key()},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        current = data.get("c", 0) or data.get("pc", 0)  # fall back to prev_close when market closed
        prev_close = data.get("pc", 0)
        change = current - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "ticker": ticker,
            "current": current,
            "open": data.get("o", 0) or current,
            "high": data.get("h", 0) or current,
            "low": data.get("l", 0) or current,
            "prev_close": prev_close,
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
        }


async def get_company_news(ticker: str, days: int = 7) -> list[dict]:
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{FINNHUB_BASE}/company-news",
            params={"symbol": ticker, "from": from_date, "to": to_date, "token": _api_key()},
            timeout=10,
        )
        r.raise_for_status()
        articles = r.json()
        return [
            {
                "headline": a.get("headline", ""),
                "summary": a.get("summary", "")[:300],
                "source": a.get("source", ""),
                "datetime": datetime.fromtimestamp(a.get("datetime", 0)).strftime("%Y-%m-%d %H:%M"),
            }
            for a in (articles or [])[:10]
        ]


async def get_news_sentiment(ticker: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{FINNHUB_BASE}/news-sentiment",
            params={"symbol": ticker, "token": _api_key()},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        sentiment = data.get("sentiment", {})
        return {
            "ticker": ticker,
            "bullish_pct": sentiment.get("bullishPercent", 0),
            "bearish_pct": sentiment.get("bearishPercent", 0),
            "score": sentiment.get("bullishPercent", 0.5) - sentiment.get("bearishPercent", 0.5),
            "article_mentions": data.get("buzz", {}).get("articlesInLastWeek", 0),
            "weekly_average": data.get("buzz", {}).get("weeklyAverage", 0),
        }


async def get_basic_financials(ticker: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{FINNHUB_BASE}/stock/metric",
            params={"symbol": ticker, "metric": "all", "token": _api_key()},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        m = data.get("metric", {})
        return {
            "ticker": ticker,
            "pe_ratio": m.get("peBasicExclExtraTTM"),
            "eps": m.get("epsBasicExclExtraAnnual"),
            "52w_high": m.get("52WeekHigh"),
            "52w_low": m.get("52WeekLow"),
            "market_cap": m.get("marketCapitalization"),
            "beta": m.get("beta"),
            "revenue_growth": m.get("revenueGrowthTTMYoy"),
            "gross_margin": m.get("grossMarginTTM"),
        }


async def get_candles(ticker: str, resolution: str = "5", count: int = 78) -> list[dict]:
    """Fetch intraday candles. resolution in minutes: 1, 5, 15, 30, 60."""
    to_ts = int(datetime.now().timestamp())
    from_ts = to_ts - count * int(resolution) * 60
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{FINNHUB_BASE}/stock/candle",
            params={
                "symbol": ticker,
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
                "token": _api_key(),
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("s") != "ok":
            return []
        return [
            {
                "t": datetime.fromtimestamp(t).strftime("%H:%M"),
                "o": o, "h": h, "l": l, "c": c, "v": v,
            }
            for t, o, h, l, c, v in zip(
                data["t"], data["o"], data["h"], data["l"], data["c"], data["v"]
            )
        ]
