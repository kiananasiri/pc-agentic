from agno.agent import Agent
from agno.models.openai import OpenAIChat
from .tools.web_tools import web_search

def get_reactive_agent(model_name: str = "gpt-4o-mini") -> Agent:
    """
    Constructs and returns an Agno Agent for general market queries and web search lookups.
    """
    system_instructions = [
        "You are a knowledgeable cryptocurrency assistant equipped with live web search capabilities.",
        "MANDATORY TOOL USAGE: You MUST execute the `web_search` tool whenever the user asks about recent news, current events, live price updates, or market developments. NEVER state that you cannot access real-time news without calling `web_search` first.",
        "Provide clear, well-structured, and helpful answers based on the search results.",
        "CRITICAL FORMATTING RULE: ALWAYS wrap any code snippets or scripts inside Markdown triple backticks code blocks with language specifiers (e.g. ```python ... ```). NEVER output un-fenced raw code.",
        "CRITICAL LANGUAGE MANDATE: You MUST ALWAYS generate your ENTIRE output (all text, headings, analysis, recommendations, thoughts, and explanations) strictly in PERSIAN (Farsi / فارسی). NEVER output explanations or analysis in English. Present all text and explanations in Persian."
    ]

    agent = Agent(
        model=OpenAIChat(id=model_name),
        tools=[web_search],
        instructions=system_instructions,
        markdown=True,
    )
    return agent
