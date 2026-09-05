from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from .tools.ta_tools import TAToolKit

def get_technical_agent(analysis_data: Dict[str, Any], model_name: str = "gpt-4o-mini") -> Agent:
    """
    Constructs and returns an Agno Agent for Technical Analysis equipped with chart tools.
    """
    ta_toolkit = TAToolKit(analysis_data)
    tools = ta_toolkit.create_tools()

    system_instructions = [
        "You are an expert Cryptocurrency Technical Analysis Agent.",
        "Use your available tools to inspect chart metadata, price statistics, OHLCV candles, and technical indicators.",
        "Do NOT assume missing data; call `get_indicator_data`, `get_recent_candles`, or `get_price_statistics` to fetch facts on demand.",
        "Analyze trends, support/resistance levels, momentum, and indicator signals (e.g. Aroon crossovers, CCI overbought/oversold, KVO volume trends, RSI, MACD).",
        "If the user asks for trading signals or recommendations (Long/Short), specify:",
        "  - Direction (Long or Short)",
        "  - Entry Price / Zone",
        "  - Stop Loss (SL)",
        "  - Take Profit Targets (TP1, TP2, TP3)",
        "  - Risk to Reward (R:R) ratio (ensure R:R >= 1.0)",
        "CRITICAL FORMATTING RULE: ALWAYS wrap any code snippets, python scripts, or pine scripts inside Markdown triple backticks code blocks with language specifiers (e.g. ```python ... ```). NEVER output un-fenced raw code.",
        "CRITICAL LANGUAGE MANDATE: You MUST ALWAYS generate your ENTIRE output (all text, headings, analysis, recommendations, thoughts, and explanations) strictly in PERSIAN (Farsi / فارسی). NEVER output explanations or analysis in English. Even if indicator names or tool inputs are in English, present all text and explanations in Persian."
    ]

    agent = Agent(
        model=OpenAIChat(id=model_name),
        tools=tools,
        instructions=system_instructions,
        markdown=True,
    )
    return agent
