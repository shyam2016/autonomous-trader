import json
import logging
import os
from datetime import datetime, timezone
import anthropic
from backend.services import finnhub

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "get_stock_quote",
        "description": "Get the current real-time stock quote including price, open, high, low, and daily change.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_company_news",
        "description": "Get recent news articles for a stock from the last 7 days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                "days": {"type": "integer", "description": "Number of days of news to retrieve (default 7)", "default": 7},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_news_sentiment",
        "description": "Get aggregated news sentiment score for a stock — bullish %, bearish %, and overall score.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_basic_financials",
        "description": "Get fundamental financial metrics: P/E ratio, EPS, 52-week high/low, market cap, beta.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert stock market research analyst. Your job is to analyze a given stock and produce a comprehensive research report.

Use the available tools to gather:
1. Current price and trading data
2. Recent news (last 7 days)
3. News sentiment analysis
4. Key financial fundamentals

After gathering data, produce a JSON research report with EXACTLY this structure:
{
  "ticker": "SYMBOL",
  "current_price": <float>,
  "sentiment_score": <float between -1.0 (very bearish) and 1.0 (very bullish)>,
  "key_news": ["headline 1", "headline 2", "headline 3"],
  "bull_thesis": "<2-3 sentence bullish argument>",
  "bear_thesis": "<2-3 sentence bearish argument>",
  "recommendation": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": <float between 0.0 and 1.0>
}

Be objective. Base your analysis on facts from the data. Return ONLY valid JSON in your final response — no markdown, no extra text."""


async def _execute_tool(name: str, tool_input: dict) -> str:
    try:
        if name == "get_stock_quote":
            result = await finnhub.get_quote(tool_input["ticker"])
        elif name == "get_company_news":
            result = await finnhub.get_company_news(tool_input["ticker"], tool_input.get("days", 7))
        elif name == "get_news_sentiment":
            result = await finnhub.get_news_sentiment(tool_input["ticker"])
        elif name == "get_basic_financials":
            result = await finnhub.get_basic_financials(tool_input["ticker"])
        else:
            result = {"error": f"Unknown tool: {name}"}
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def run(ticker: str) -> dict:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": f"Research the stock {ticker} and produce a complete research report."}]

    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    text = block.text.strip()
                    # Strip markdown code fences if present
                    if text.startswith("```"):
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]
                    try:
                        report = json.loads(text)
                        report["timestamp"] = datetime.now(timezone.utc).isoformat()
                        logger.info(
                            f"[Researcher] {ticker}: {report.get('recommendation')} "
                            f"| price=${report.get('current_price')} "
                            f"| sentiment={report.get('sentiment_score')} "
                            f"| confidence={report.get('confidence')}"
                        )
                        return report
                    except json.JSONDecodeError:
                        pass
            # Fallback if JSON parsing fails
            return {
                "ticker": ticker,
                "current_price": 0,
                "sentiment_score": 0,
                "key_news": [],
                "bull_thesis": "Unable to parse research.",
                "bear_thesis": "Unable to parse research.",
                "recommendation": "NEUTRAL",
                "confidence": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            break

    return {"ticker": ticker, "error": "Agent did not complete", "timestamp": datetime.now(timezone.utc).isoformat()}
