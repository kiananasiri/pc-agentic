from public_app.src.prompts import (
    missing_info_response,
    system_prompt_action,
    missing_price_info_detection_prompt,
    missing_info_response,
    system_prompt_reasoning,
)
from public_app.src.utilis import (
    prompt_builder,
    chat_invoke,
    invoke,
    calculate_price,
    dialogue_builder,
)
from public_app.src.config import get_llm_name
from public_app.src.components.web_search_agent.web_search import web_search


def detect_missing_price_info(user_input, conversation_history):
    history = dialogue_builder(conversation_history)
    prompt = missing_price_info_detection_prompt.format(
        conversation_history=history,
        user_message=user_input,
    )

    response, _, _ = invoke(prompt)
    return "yes" in response.lower()


def reactive_answering(user_input, conversation_history, image_documents=None):
    """
    Generate a response to user input based on conversation history using a two-step process:
    reasoning and action generation.

    Args:
        user_input (str): The current message from the user
        conversation_history (list): List of previous conversation messages

    Returns:
        str: Generated response action based on reasoning and conversation context

    This function implements a two-stage response generation:
    1. First generates reasoning about how to respond using reasoning prompt
    2. Then generates actual response action based on the reasoning

    Token usage is tracked for both API calls but not returned.
    """
    missing_price_info = detect_missing_price_info(user_input, conversation_history)
    if missing_price_info:
        return {
            "status": 0,
            "answer": missing_info_response,
            "price": 0,
        }
    web_search_result = web_search(user_input, conversation_history)
    input_tokens = output_tokens = 0

    reasoning_prompt = prompt_builder(
        history=conversation_history,
        new_message=user_input,
        system_prompt=system_prompt_reasoning.format(
            web_search_result=web_search_result
        ),
        image_documents=image_documents,
    )
    reasoning, in_t, ou_t = chat_invoke(reasoning_prompt)
    input_tokens += in_t
    output_tokens += ou_t

    action_prompt = prompt_builder(
        history=conversation_history,
        new_message=user_input,
        system_prompt=system_prompt_action.format(reasoning=reasoning),
        image_documents=image_documents,
    )
    action, in_t, ou_t = chat_invoke(action_prompt)
    input_tokens += in_t
    output_tokens += ou_t

    return {
        "status": 0,
        "answer": action,
        "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
    }
