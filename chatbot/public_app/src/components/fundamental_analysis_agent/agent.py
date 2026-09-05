import time
from .tool import (
    retry_plan_fundamental_analysis,
    fundamental_plan_creation,
    applying_strategy_prompt_chooser,
    summary_prompt_chooser,
)
from public_app.src.utilis import (
    calculate_price,
    leakage_detection,
    remove_unwanted_text,
    parse_json_answer,
)
from public_app.src.config import get_llm_name
from public_app.src.prompts import (fundamental_applying_plans_error_handelling_prompt, 
                                    fundamental_applying_plans_prompt,
                                    plans_parsing_error_handelling_prompt,
                                )
from public_app.src.utilis import invoke
from ast import literal_eval

def fundamental_analysis_agent(
    fundamental_analysis, user_query, image_documents, history
):
    """
    Analyze the fundamental data of a cryptocurrency.
    """
    strategy = fundamental_analysis.get('strategy' , '').lower().replace(' ', '').replace('_', '').strip()
    (
        plans,
        input_tokens,
        output_tokens,
    ) = fundamental_plan_creation(
        fundamental_analysis, strategy ,user_query, image_documents, history
    )
    leakage, in_t, out_t = leakage_detection(plans)
    input_tokens += in_t
    output_tokens += out_t
    if leakage:
        plans, input_t, output_t = retry_plan_fundamental_analysis(
            fundamental_analysis, strategy, user_query, image_documents, history
        )
        input_tokens += input_t
        output_tokens += output_t


    answer, input_tokens, output_tokens = apply_steps(
        plans, strategy, user_query, fundamental_analysis
    )

    leakage, in_t, out_t = leakage_detection(answer)
    if leakage:
        for i in range(5):
            answer, in_t, out_t = apply_steps(
                plans, strategy, user_query, fundamental_analysis,
            )
            input_tokens += in_t
            output_tokens += out_t
            leakage, in_t, out_t = leakage_detection(answer)
            input_tokens += in_t
            output_tokens += out_t
            if not leakage:
                break

    return {
        "status": 0,
        "answer": answer,
        "price": calculate_price(input_tokens, output_tokens),
    }


def handle_plan_parsing_error(plans, user_query, fundamental_data):
    """
    Handles errors when parsing the JSON plan for fundamental analysis fails.
    Instead of applying each parsed plan step-by-step, it applies the entire plan in a single prompt.

    Args:
        plans: The original (possibly unparsed) plan text
        user_query: The user's original query
        fundamental_data: Dictionary of fundamental data including market, pair, and data fields

    Returns:
        tuple: (answer, input_tokens, output_tokens)
    """
    is_persian = any("\u0600" <= char <= "\u06ff" for char in user_query)
    data_keys = list(fundamental_data.get("data", {}).keys())
    asset = fundamental_data.get("asset", "")
    chain = fundamental_data.get("chain", "")
    market = fundamental_data.get("market", "")
    data = fundamental_data.get("data", {})
    
    plan_of_step = plans_parsing_error_handelling_prompt.format(
        language="Persian" if is_persian else "English",
        data_keys=data_keys,
        data=data,
        plan=plans,
    )

    prompt = fundamental_applying_plans_error_handelling_prompt.format(
        today_date=time.strftime("%Y-%m-%d"),
        plan_of_step=plan_of_step,
        results=f"Generate the answer in one step using the full plan and fundamental data. Maintain the language of the user query: {user_query}",
        asset_symbol=asset['symbol'],
        asset_name=asset["name"],
        chain_name=chain["name"],
        startDate=fundamental_data.get("startDate", ""),
        endDate=fundamental_data.get("endDate", ""),
        market=market,
        user_query=user_query,
    )

    answer, in_t, out_t = invoke(prompt=prompt)
    answer = remove_unwanted_text(answer)

    return answer, in_t, out_t


def apply_steps(
    plan,
    strategy,
    user_query,
    fundamental_data,
):
    data_keys = fundamental_data.get('data', {}).copy()
    currency_market = fundamental_data.get("market", None)
    currency_symbol = fundamental_data.get("pair", None)
    startDate = fundamental_data.get("startDate", "")
    endDate = fundamental_data.get("endDate", "")
    market = fundamental_data.get("market", "")
    asset = fundamental_data.get("asset", {})
    chain = fundamental_data.get("chain", {})
    results = ""

    input_tokens = 0
    output_tokens = 0
    strategy_prompt = applying_strategy_prompt_chooser(strategy)
    strategy_formatted_prompt = strategy_prompt.format(
        properties="",
        startDate=startDate,
        endDate=endDate,
        market=market,
        asset_symbol=asset["symbol"],
        asset_name=asset["name"],
        chain_name=chain["name"],
    )
    try:
        plan = parse_json_answer(plan)
        if not isinstance(plan, dict):
            plan = literal_eval(plan)
    except Exception:
        return handle_plan_parsing_error(plan, user_query, fundamental_data)
        
    plan_len = len(plan.get("steps", {}))    
    data_keys_len = len(data_keys)
    if plan_len < data_keys_len:
        for i in range(data_keys_len - plan_len):
            plan["steps"][plan_len + i] = {}
    elif data_keys_len < plan_len:
        for i in range(plan_len - data_keys_len):
            data_keys[data_keys_len + i] = {}
            
    steps = plan.get("steps", {})
    
    for key, (step_number, step_plan) in zip(data_keys, steps.items()):
        plan = step_plan.get("plan" , "")
        if not plan:
            plan = ""
        
        prompt = fundamental_applying_plans_prompt.format(
            today_date=time.strftime("%Y-%m-%d"),
            strategy=strategy_formatted_prompt,
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            fundamental_data_field_description=key,
            fundamental_data_provided=data_keys,
            results=results,
            plan_of_step=plan,
            step=plan,
            user_query=user_query,
        )
        answer, in_t, out_t = invoke(prompt=prompt)
        answer = remove_unwanted_text(answer)
        results += "\n" + answer
        input_tokens += in_t
        output_tokens += out_t

    summarizer = summary_prompt_chooser(strategy)
    if summarizer:
        summarizer = summarizer.format(results=results,
                                       asset_symbol=asset["symbol"],
                                       market=market,
                                       startDate=startDate,
                                       endDate=endDate,
                                       )
        summarizer_answer, in_t, out_t = invoke(prompt=summarizer)
        summarizer_answer = remove_unwanted_text(summarizer_answer)
        results += "\n" + summarizer_answer
        return summarizer_answer, input_tokens, output_tokens
    
    return answer, input_tokens, output_tokens
