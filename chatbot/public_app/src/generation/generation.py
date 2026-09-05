from public_app.src.prompts import (
    system_prompt_reasoning,
    system_prompt_action,
    web_search_router_prompt,
    technical_analysis_prompt,
    applying_plans_prompt,
    coding_agent_prompt,
    code_applying_plans_prompt,
    validator_prompt,
    debugger_prompt,
    system_prompt_temp_technical_analysis,
    missing_price_info_detection_prompt,
    missing_info_response,
    preprocess_analysis_input_prompt,
)
from public_app.src.utilis import (
    calculate_price,
    prompt_builder,
    chat_invoke,
    invoke,
    count_refinement_steps,
    ask_ddg,
    parse_json_answer,
    extract_code,
    dialogue_builder,
    parse_list_answer,
)
from public_app.src.config import get_llm_name
from ast import literal_eval


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
    input_tokens, output_tokens = 0, 0
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


def code_planner(history, user_query, image_documents):
    planner_prompt = prompt_builder(
        history=history,
        new_message=user_query,
        system_prompt=coding_agent_prompt,
        image_documents=image_documents,
    )
    plans, in_t, out_t = chat_invoke(planner_prompt)
    return plans, in_t, out_t


def code_applying_plans(user_query, plans, input_tokens, output_tokens):
    try:
        plans = parse_json_answer(plans)
        plans = literal_eval(plans)
    except Exception as e:
        prompt = code_applying_plans_prompt.format(
            user_query=user_query,
            plan=plans,
            results="",
            step=(
                """this is the last step, 
                so merge all previously generated codes in last steps and generate final code;
                in this step your explanation should be in same language as user query"""
            ),
        )
        answer, in_t, out_t = invoke(prompt=prompt)
        input_tokens += in_t
        output_tokens += out_t

        return answer, input_tokens, output_tokens

    step_count = len(plans)
    results = ""
    for i, plan in enumerate(plans.values()):
        prompt = code_applying_plans_prompt.format(
            user_query=user_query,
            plan=plan,
            results=results if i > 0 else "",
            step=(
                f"this is the only do what the step  number {i + 1} so only do what instruction says and do not generate the final code, the final code will be generated at the last step"
                if i < step_count - 1
                else """this is the last step, 
                so merge all previously generated codes in last steps and generate final code;
                in this step your explanation should be in same language as user query"""
            ),
        )
        answer, in_t, out_t = invoke(prompt=prompt)
        input_tokens += in_t
        output_tokens += out_t
        results += f"step{i} results: {answer}"

    return answer, input_tokens, output_tokens


def validator(history, code, user_query, image_documents, plans):
    prompt = prompt_builder(
        new_message=user_query,
        history=history,
        image_documents=image_documents,
        system_prompt=validator_prompt.format(code=code, plans=plans),
    )
    validation, input_tokens, output_tokens = chat_invoke(prompt)
    return validation, input_tokens, output_tokens


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
            code=extract_code,
            user_query=user_query,
            image_documents=image_documents,
            plans=plans,
        )
        input_tokens += input_tokens_debugger
        output_tokens += output_tokens_debugger
        return {
            "status": 0,
            "answer": answer,
            "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
        }

    return {
        "status": 0,
        "answer": answer.get("response"),
        "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
    }


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


def preprocess_analysis_input(user_input):
    prompt = preprocess_analysis_input_prompt.format(user_input=user_input)
    queries, in_t, out_t = invoke(prompt=prompt)
    try:
        queries = literal_eval(parse_json_answer(queries)).get("queries")
        list_of_queries = parse_list_answer(queries)
        for i, query in enumerate(list_of_queries, start=1):
            list_of_queries[i - 1] = f"User Query{i}: " + query

        return (
            f"These are queries (1 to {len(list_of_queries)}), You should consider :\n"
            + "\n".join(list_of_queries),
            len(list_of_queries),
            in_t,
            out_t,
        )

    except Exception as e:
        return queries, None, in_t, out_t
