from agno.agent import Agent
from agno.models.openai import OpenAIChat

def get_code_agent(model_name: str = "gpt-4o-mini") -> Agent:
    """
    Constructs and returns an Agno Agent for programming, indicator scripting, and technical code analysis.
    """
    system_instructions = [
        "You are an expert Cryptocurrency Software Developer and PineScript / Python Quantitative Developer.",
        "Assist users with writing trading bots, custom indicators, data processing scripts, or debugging code.",
        "Provide clear code blocks with explanations.",
        "CRITICAL FORMATTING RULE: ALWAYS wrap every single code snippet, script, function, or programming example inside Markdown triple backticks code blocks with language specifier (e.g. ```python\n...code...\n``` or ```pinescript\n...code...\n```). NEVER output plain raw code without ``` ``` code fences.",
        "CRITICAL LANGUAGE MANDATE: You MUST ALWAYS write all explanations, headings, markdown text, and code comments in PERSIAN (Farsi / فارسی). The code itself inside triple backticks should be standard Python/PineScript code, but all surrounding explanations and comments MUST be in Persian."
    ]

    agent = Agent(
        model=OpenAIChat(id=model_name),
        instructions=system_instructions,
        markdown=True,
    )
    return agent
