from public_app.src.prompts import query_refinement_with_question , user_input_refinement_prompt
from public_app.src.utilis import (
    parse_json_answer,
    invoke
)
from ast import literal_eval

def user_input_refinement(user_input):
    formatted_prompt = user_input_refinement_prompt.format(user_input=user_input)
    answer = invoke(prompt=formatted_prompt)[0]
    try:
        answer = parse_json_answer(answer)
        return literal_eval(answer).get("refined_input")
    except:
        return user_input
        