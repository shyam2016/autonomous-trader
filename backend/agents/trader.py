import json
import os
from datetime import datetime, timezone
import anthropic
from backend.services import portfolio as portfolio_svc

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "get_portfolio",
        "description": "Get the current paper trading portfolio: cash balance, all positions, total value, and P&L.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_position",
        "description": "Get the current holding for a specific ticker (qty and avg cost).",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_max_buy_quantity",
        "description": "Get the maximum number of shares you can buy for a ticker at the given price, respecting the 10% portfolio position limit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "price": {"type": "number"},
            },
            "required": ["ticker", "price"],
        },
    },
    {
        "name": "buy_stock",
        "description": "Execute a paper buy order for a stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "quantity": {"type": "number", "description": "Number of shares to buy"},
                "price": {"type": "number", "description": "Current market price per share"},
                "rationale": {"type": "string", "description": "Brief reason for buying"},
            },
            "required": ["ticker", "quantity", "price", "rationale"],
        },
    },
    {
        "name": "sell_stock",
        "description": "Execute a paper sell order for a stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "quantity": {"type": "number", "description": "Number of shares to sell"},
                "price": {"type": "number", "description": "Current market price per share"},
                "rationale": {"type": "string", "description": "Brief reason for selling"},
            },
            "required": ["ticker", "quantity", "price", "rationale"],
        },
    },
]

SYSTEM_PROMPT = """You are an autonomous paper trading agent for a $100,000 virtual portfolio.

Risk rules you MUST follow:
- Maximum 10% of total portfolio value in any single stock
- Never sell more shares than you currently hold
- Stop-loss: if a position is down more than 8%, sell it
- Only buy when confidence from research is >= 0.6 and recommendation is BULLISH
- Only sell (beyond stop-loss) when recommendation is BEARISH and you hold the stock
- Otherwise HOLD

Your workflow:
1. Check the current portfolio and position for this ticker
2. Check max buy quantity if considering a purchase
3. Make a trading decision based on the research report provided
4. Execute the trade (buy or sell) if warranted, or do nothing (hold)
5. Return a JSON decision summary

Return ONLY this JSON at the end (no markdown, no extra text):
{
  "ticker": "SYMBOL",
  "action": "BUY" | "SELL" | "HOLD",
  "quantity": <float or 0 if HOLD>,
  "rationale": "<concise explanation of decision>"
}"""


async def _execute_tool(name: str, tool_input: dict) -> str:
    try:
        if name == "get_portfolio":
            p = await portfolio_svc.get_portfolio()
            return json.dumps(p.model_dump())
        elif name == "get_position":
            pos = await portfolio_svc.get_position(tool_input["ticker"])
            return json.dumps(pos.model_dump() if pos else {"ticker": tool_input["ticker"], "qty": 0, "avg_cost": 0})
        elif name == "get_max_buy_quantity":
            qty = await portfolio_svc.max_buy_quantity(tool_input["ticker"], tool_input["price"])
            return json.dumps({"max_quantity": qty})
        elif name == "buy_stock":
            trade = await portfolio_svc.buy(
                tool_input["ticker"],
                tool_input["quantity"],
                tool_input["price"],
                tool_input.get("rationale", ""),
            )
            return json.dumps(trade.model_dump())
        elif name == "sell_stock":
            trade = await portfolio_svc.sell(
                tool_input["ticker"],
                tool_input["quantity"],
                tool_input["price"],
                tool_input.get("rationale", ""),
            )
            return json.dumps(trade.model_dump())
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def run(research_report: dict) -> dict:
    ticker = research_report.get("ticker", "")
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_message = f"""Research report for {ticker}:
{json.dumps(research_report, indent=2)}

Based on this research, make a trading decision for {ticker}."""

    messages = [{"role": "user", "content": user_message}]

    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
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
                    if text.startswith("```"):
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]
                    try:
                        decision = json.loads(text)
                        decision["timestamp"] = datetime.now(timezone.utc).isoformat()
                        return decision
                    except json.JSONDecodeError:
                        pass
            return {
                "ticker": ticker,
                "action": "HOLD",
                "quantity": 0,
                "rationale": "Could not parse decision",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            break

    return {
        "ticker": ticker,
        "action": "HOLD",
        "quantity": 0,
        "rationale": "Agent did not complete",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
