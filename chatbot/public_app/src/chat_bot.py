from public_app.src.agno_agents import run_agno_chat
from public_app.src.config import initialize

def chat(
    user_input,
    conversation_history=None,
    image_documents=None,
    analysis=None,
    fundamental=None,
    selected_indicators=None,
    code=False,
    model="gpt-4o-mini",
    reasoning="medium",
):
    """
    Processes the user input and generates a response using the Agno agentic architecture.
    """
    initialize(model, reasoning)

    try:
        answer = run_agno_chat(
            user_input=user_input,
            conversation_history=conversation_history,
            image_documents=image_documents,
            analysis=analysis,
            fundamental=fundamental,
            selected_indicators=selected_indicators,
            code=code,
            model=model,
            reasoning=reasoning,
        )
        return answer
    except Exception as ex:
        print(f"Agno Agent execution error: {ex}. Falling back to legacy execution.")
        # Fallback implementation if needed
        from public_app.src.components.code_agent import code_agent
        from public_app.src.components.technical_analysis_agent import technical_analysis_agent
        from public_app.src.components.web_search_agent.reactive import reactive_answering
        from public_app.src.components.fundamental_analysis_agent.agent import (
            fundamental_analysis_agent,
        )

        if code:
            return code_agent(
                history=conversation_history,
                user_query=user_input,
                image_documents=image_documents,
            )
        elif analysis:
            return technical_analysis_agent(
                history=conversation_history,
                user_query=user_input,
                image_documents=image_documents,
                analysis=analysis.copy(),
            )
        elif fundamental:
            return fundamental_analysis_agent(
                history=conversation_history,
                user_query=user_input,
                image_documents=image_documents,
                fundamental_analysis=fundamental.copy(),
            )
        else:
            return reactive_answering(
                user_input=user_input,
                conversation_history=conversation_history,
                image_documents=image_documents,
            )










