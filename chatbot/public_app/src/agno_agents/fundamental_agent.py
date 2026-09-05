from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from .tools.fundamental_tools import FundamentalToolKit

def get_fundamental_agent(fundamental_data: Dict[str, Any], model_name: str = "gpt-4o-mini") -> Agent:
    """
    Constructs and returns an Agno Agent for Fundamental & On-Chain Analysis equipped with fundamental data tools.
    """
    f_toolkit = FundamentalToolKit(fundamental_data)
    tools = f_toolkit.create_tools()

    system_instructions = [
        "You are an expert On-Chain & Fundamental Cryptocurrency Analysis Agent.",
        "Use your available tools to inspect metadata, list available metrics, and fetch time-series values or summaries on demand.",
        "Do NOT guess metric data. Always call `get_metric_data` or `get_metric_summary` for specific metric fields (e.g. `exchangeFlow`, `largeHoldersNetflow`, `bullsAndBears`, `bidAskSpread`, `averageBalance`).",
        "Evaluate overall market sentiment, whale behavior, smart money movement, or miner accumulation/distribution based on the strategy in context.",
        "Synthesize your findings into a clear, professional summary with actionable insights.",
        "CRITICAL FORMATTING RULE: ALWAYS wrap any code snippets or scripts inside Markdown triple backticks code blocks with language specifiers (e.g. ```python ... ```). NEVER output un-fenced raw code.",
        "CRITICAL LANGUAGE MANDATE: You MUST ALWAYS generate your ENTIRE output (all text, headings, analysis, recommendations, thoughts, and explanations) strictly in PERSIAN (Farsi / فارسی). NEVER output explanations or analysis in English. Even if metric names or data inputs are in English, present all text and explanations in Persian."
    ]

    agent = Agent(
        model=OpenAIChat(id=model_name),
        tools=tools,
        instructions=system_instructions,
        markdown=True,
    )
    return agent
