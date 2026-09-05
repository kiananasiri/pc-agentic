import tiktoken
from typing import Dict, Any, Optional, List
from public_app.src.utilis import calculate_price
from .technical_agent import get_technical_agent
from .fundamental_agent import get_fundamental_agent
from .reactive_agent import get_reactive_agent
from .code_agent import get_code_agent

def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Fall back token counter using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text or ""))

def format_history_context(history: Optional[List[Dict[str, Any]]]) -> str:
    """Formats conversation history array into text block."""
    if not history:
        return ""
    formatted = ["--- Conversation History ---"]
    for msg in history:
        q = msg.get("question") or msg.get("user") or ""
        a = msg.get("answer") or msg.get("assistant") or ""
        if q:
            formatted.append(f"User: {q}")
        if a:
            formatted.append(f"Assistant: {a}")
    return "\n".join(formatted) + "\n-----------------------------\n"

def run_agno_chat(
    user_input: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    image_documents: Optional[Any] = None,
    analysis: Optional[Dict[str, Any]] = None,
    fundamental: Optional[Dict[str, Any]] = None,
    selected_indicators: Optional[Dict[str, Any]] = None,
    code: bool = False,
    model: str = "gpt-4o-mini",
    reasoning: str = "medium",
) -> Dict[str, Any]:
    """
    Main entry point for Agno Agent Orchestrator.
    Routes user requests to specialized Agno Agents equipped with targeted data tools.
    """
    # Dynamically fetch live today's TA and fundamental metrics if payloads are missing or requested
    try:
        from public_app.src.market_data_service import auto_enrich_payloads
        analysis, fundamental = auto_enrich_payloads(user_input, analysis, fundamental, selected_indicators)
    except Exception as e:
        print(f"[Orchestrator] Warning: Failed to auto-enrich live market data: {e}")

    history_context = format_history_context(conversation_history)
    
    indicator_notes = ""
    if isinstance(selected_indicators, dict):
        ta_list = selected_indicators.get("technical") or []
        fa_list = selected_indicators.get("fundamental") or []
        parts = []
        if ta_list:
            parts.append(f"Technical Indicators requested by user: {', '.join(ta_list)}")
        if fa_list:
            parts.append(f"On-Chain/Fundamental Metrics requested by user: {', '.join(fa_list)}")
        if parts:
            indicator_notes = f"[User Active Selections: {' | '.join(parts)}]\n"

    prompt_text = f"{history_context}{indicator_notes}User Query: {user_input}"

    # Agent Selection Strategy
    from .tools.web_tools import web_search
    if code:
        agent = get_code_agent(model_name=model)
    elif analysis and fundamental:
        # Combined analysis query: instantiate TA agent with FA tools attached
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat
        from .tools.ta_tools import TAToolKit
        from .tools.fundamental_tools import FundamentalToolKit

        ta_tools = TAToolKit(analysis).create_tools()
        fa_tools = FundamentalToolKit(fundamental).create_tools()
        combined_tools = ta_tools + fa_tools + [web_search]

        agent = Agent(
            model=OpenAIChat(id=model),
            tools=combined_tools,
            instructions=[
                "You are an expert Cryptocurrency Analyst specializing in Technical, On-Chain/Fundamental analysis, and live market news.",
                "Use available technical, fundamental, or web_search tools to inspect indicators, candles, metrics, or recent news as needed.",
                "Synthesize a complete market analysis addressing price action, fundamental metrics, and real-time news when applicable.",
                "CRITICAL FORMATTING RULE: ALWAYS wrap any code snippets or scripts inside Markdown triple backticks code blocks with language specifiers (e.g. ```python ... ```). NEVER output un-fenced raw code.",
                "CRITICAL LANGUAGE MANDATE: You MUST ALWAYS generate your ENTIRE output (all text, headings, analysis, recommendations, thoughts, and explanations) strictly in PERSIAN (Farsi / فارسی). NEVER output explanations or analysis in English. Present all text and explanations in Persian."
            ],
            markdown=True,
        )
    elif analysis:
        agent = get_technical_agent(analysis_data=analysis, model_name=model)
        agent.tools.append(web_search)
    elif fundamental:
        agent = get_fundamental_agent(fundamental_data=fundamental, model_name=model)
        agent.tools.append(web_search)
    else:
        agent = get_reactive_agent(model_name=model)

    # Execute Agno Agent
    run_output = agent.run(prompt_text)

    # Extract Answer Text
    answer_text = str(run_output.content) if run_output and run_output.content else "No response generated."

    # Extract Token Metrics
    metrics = getattr(run_output, "metrics", None)
    input_tokens = None
    output_tokens = None

    if metrics:
        if isinstance(metrics, dict):
            input_tokens = metrics.get("input_tokens") or metrics.get("prompt_tokens")
            output_tokens = metrics.get("output_tokens") or metrics.get("completion_tokens")
        else:
            input_tokens = getattr(metrics, "input_tokens", None)
            output_tokens = getattr(metrics, "output_tokens", None)

    if not input_tokens:
        input_tokens = estimate_tokens(prompt_text, model=model)
    if not output_tokens:
        output_tokens = estimate_tokens(answer_text, model=model)

    price = calculate_price(input_tokens, output_tokens, model=model)

    # Extract Reasoning / Thinking Process
    thinking_text = ""
    raw_reasoning = getattr(run_output, "reasoning_content", None)
    if raw_reasoning:
        thinking_text = str(raw_reasoning)
    else:
        thinking_steps = []
        thinking_steps.append("1. 🧠 تحلیل اولیه پرسش و انتخاب ایجنت Agno")
        if analysis:
            pair = analysis.get("pair", "BTCUSDT")
            thinking_steps.append(f"2. 📈 دریافت داده‌های زنده و محاسبه اندیکاتورهای RSI, MACD, Moving Averages برای {pair}")
        if fundamental:
            asset = fundamental.get("asset", {}).get("symbol", "BTC")
            thinking_steps.append(f"3. 🔗 آنالیز جریان‌های آن‌چین، پول هوشمند و رفتار ماینرها برای {asset}")
        thinking_steps.append("4. ⚡ ترکیب شواهد تحلیلی و استخراج پاسخ و سیگنال نهایی")
        thinking_text = "\n".join(thinking_steps)

    return {
        "status": 0,
        "answer": answer_text,
        "price": price,
        "thinking": thinking_text,
    }
