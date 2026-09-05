from public_app.src.prompts import debugger_prompt
from public_app.src.utilis import prompt_builder, chat_invoke


def debugger(history, explaination, code, user_query, image_documents, plans):
    prompt = prompt_builder(
        history=history,
        new_message=user_query,
        image_documents=image_documents,
        system_prompt=debugger_prompt.format(
            code=code, explaination=explaination, plans=plans
        ),
    )

    debugging, input_tokens, output_tokens = chat_invoke(prompt)
    return debugging, input_tokens, output_tokens
