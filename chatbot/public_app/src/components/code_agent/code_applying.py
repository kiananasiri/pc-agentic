from public_app.src.prompts import code_applying_plans_prompt
from public_app.src.utilis import invoke, parse_json_answer
from ast import literal_eval


def code_applying_plans(user_query, plans, input_tokens, output_tokens):
    try:
        plans = parse_json_answer(plans)
        plans = literal_eval(plans)
    except Exception as e:
        return handle_parsing_error(
            user_query=user_query,
            plans=plans,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    step_count = len(plans)
    results = ""
    for i, plan in enumerate(plans.values()):
        is_final_step = i == step_count - 1
        step_instruction = get_step_instruction(i, is_final_step)

        prompt = code_applying_plans_prompt.format(
            user_query=user_query,
            plan=plan,
            results=results if i > 0 else "",
            step=step_instruction,
        )
        answer, in_t, out_t = invoke(prompt=prompt)
        input_tokens += in_t
        output_tokens += out_t
        results += f"step{i} results: {answer}"

    return answer, input_tokens, output_tokens


def handle_parsing_error(user_query, plans, input_tokens, output_tokens):
    prompt = code_applying_plans_prompt.format(
        user_query=user_query,
        plan=plans,
        results="",
        step=(
            """Consider all plans and generate the final code; in this step your explanation should be in same language as user query is in"""
        ),
    )
    answer, input_t, output_t = invoke(prompt=prompt)
    input_tokens += input_t
    output_tokens += output_t
    return answer, input_tokens, output_tokens


def get_step_instruction(i, is_final_step):
    if is_final_step:
        return """this is the last step, 
        so merge all previously generated codes in last steps and generate final code;
        in this step your explanation should be in same language as user query"""
    else:
        return f"this is the only do what the step  number {i + 1} so only do what instruction says and do not generate the final code, the final code will be generated at the last step"
