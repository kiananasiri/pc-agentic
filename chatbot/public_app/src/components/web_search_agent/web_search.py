from public_app.src.prompts import web_search_router_prompt
from public_app.src.utilis import prompt_builder, chat_invoke, ask_ddg


def web_search_router(user_input, conversation_history):
    prompt = prompt_builder(
        history=conversation_history,
        new_message=user_input,
        system_prompt=web_search_router_prompt,
        image_documents=None,
        consider_image=False,
    )
    is_search_needed = chat_invoke(prompt)
    return True if is_search_needed[0].lower() == "yes" else False


def web_search(user_input, history):
    is_search_needed = web_search_router(user_input, history)
    if is_search_needed:
        result = ask_ddg(user_input, history)
        return result
    else:
        return ""
