from .code_applying import code_applying_plans
from .validator import validator
from .debugger import debugger
from public_app.src.utilis import (
    parse_json_answer,
    extract_code,
    calculate_price,
    prompt_builder,
    chat_invoke,
)
from public_app.src.config import get_llm_name
from ast import literal_eval
from public_app.src.prompts import coding_agent_prompt


def code_planner(history, user_query, image_documents):
    planner_prompt = prompt_builder(
        history=history,
        new_message=user_query,
        system_prompt=coding_agent_prompt,
        image_documents=image_documents,
    )
    plans, in_t, out_t = chat_invoke(planner_prompt)
    return plans, in_t, out_t


def code_agent(history, user_query, image_documents):
    plans, input_tokens, output_tokens = code_planner(
        history=history, user_query=user_query, image_documents=image_documents
    )

    applied_plans, input_tokens_applying, output_tokens_applying = code_applying_plans(
        user_query=user_query,
        plans=plans,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    input_tokens += input_tokens_applying
    output_tokens += output_tokens_applying

    extracted_code = extract_code(applied_plans)

    try:
        validation, input_tokens_validation, output_tokens_validator = validator(
            history=history,
            code=extracted_code,
            user_query=user_query,
            image_documents=image_documents,
            plans=plans,
        )

        input_tokens += input_tokens_validation
        output_tokens += output_tokens_validator

        answer = literal_eval(parse_json_answer(validation))
        if answer.get("issues_found") == "yes":
            answer, input_tokens_debugger, output_tokens_debugger = debugger(
                history=history,
                explaination=answer.get("issues"),
                code=extracted_code,
                user_query=user_query,
                image_documents=image_documents,
                plans=plans,
            )

            input_tokens += input_tokens_debugger
            output_tokens += output_tokens_debugger

            return {
                "status": 0,
                "answer": answer,
                "price": calculate_price(
                    input_tokens, output_tokens, model=get_llm_name()
                ),
            }

        return {
            "status": 0,
            "answer": answer.get("response"),
            "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
        }

    except Exception as e:
        return {
            "status": 0,
            "answer": extracted_code,
            "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
        }
