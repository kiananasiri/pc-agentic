from public_app.src.config import get_llm, get_agent, get_llm_name

# Backwards-compatibility exports
LLM = get_llm()
agent = get_agent()
llm_name = get_llm_name()
