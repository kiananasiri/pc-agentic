from public_app.src.prompts import validator_prompt
from public_app.src.utilis import prompt_builder, chat_invoke


def validator(history, code, user_query, image_documents, plans):
    prompt = prompt_builder(
        new_message=user_query,
        history=history,
        image_documents=image_documents,
        system_prompt=validator_prompt.format(code=code, plans=plans),
    )
    validation, input_tokens, output_tokens = chat_invoke(prompt)
    return validation, input_tokens, output_tokens
