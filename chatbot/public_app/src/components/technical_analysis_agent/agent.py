from .planner import technical_analysis_plan_creation
from .tools import (
    get_tools_of_step_prompt,
    prepare_analysis_data,
    get_step_instruction,
    future_helper_agent,
    step_invoke,
)
from public_app.src.utilis import (
    get_and_parse_steps,
    parse_json_answer,
    calculate_price,
    leakage_detection,
    remove_unwanted_text,
    invoke,
    invoke_ReAct,
)
from public_app.src.config import get_llm_name
from public_app.src.prompts import (
    applying_plans_prompt,
    synced_signal_prompt,
    long_short_signals_prompt,
    error_handeling_prompt,
    error_handeling_react_prompt,
    tabular_format_prompt,
    leverage_calculation_prompt,
)
import time


def technical_analysis_agent(history, user_query, image_documents, analysis={}):
    (
        charts,
        charts_prompt,
        list_of_indicators,
        list_of_indicators_prompt,
        currency_market,
        currency_symbol,
        symbols_of_indicators,
    ) = prepare_analysis_data(analysis)
    steps, future_trading, input_tokens, output_tokens = (
        technical_analysis_plan_creation(
            history=history,
            user_query=user_query,
            image_documents=image_documents,
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            name_of_the_indicators=list_of_indicators_prompt,
            charts=charts_prompt,
        )
    )
    
    if future_trading:
        user_query += leverage_calculation_prompt


    try:
        steps = parse_json_answer(steps)
        steps = get_and_parse_steps(steps)

    except Exception as e:
        answer, in_t, out_t = handle_parsing_error(
            e,
            steps,
            charts,
            user_query,
            currency_market,
            currency_symbol,
            list_of_indicators,
        )
        input_tokens += in_t
        output_tokens += out_t
        leakage, in_t, out_t = leakage_detection(answer)
        input_tokens += in_t
        output_tokens += out_t

        if leakage:
            answer, in_t, out_t = retry_apply_steps(
                steps,
                charts,
                user_query,
                currency_market,
                currency_symbol,
                list_of_indicators,
                future_trading,
                symbols_of_indicators,
                parsed_steps=False,
            )
        return {
            "status": 0,
            "answer": answer,
            "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
        }

    answer, in_t, out_t = apply_steps(
        steps,
        charts,
        user_query,
        currency_market,
        currency_symbol,
        list_of_indicators,
        future_trading,
        symbols_of_indicators,
    )
    input_tokens += in_t
    output_tokens += out_t

    leakage, in_t, out_t = leakage_detection(answer)
    input_tokens += in_t
    output_tokens += out_t

    if leakage:
        answer, in_t, out_t = retry_apply_steps(
            steps,
            charts,
            user_query,
            currency_market,
            currency_symbol,
            list_of_indicators,
            future_trading,
            symbols_of_indicators,
        )
    input_tokens += in_t
    output_tokens += out_t

    return {
        "status": 0,
        "answer": answer,
        "price": calculate_price(input_tokens, output_tokens, model=get_llm_name()),
    }


def retry_apply_steps(
    steps,
    charts,
    user_query,
    currency_market,
    currency_symbol,
    list_of_indicators,
    future_trading,
    symbols_of_indicators,
    parsed_steps=True,
):
    detected_leakage = True
    input_tokens = output_tokens = 0

    if not parsed_steps:
        for i in range(5):
            if detected_leakage:
                answer, in_t, out_t = handle_parsing_error(
                    e="parsing error",
                    steps=steps,
                    charts=charts,
                    user_query=user_query,
                    currency_market=currency_market,
                    currency_symbol=currency_symbol,
                    list_of_indicators=list_of_indicators,
                )
                input_tokens += in_t
                output_tokens += out_t
                detected_leakage, in_t, out_t = leakage_detection(answer)
                input_tokens += in_t
                output_tokens += out_t
            else:
                break
        return answer, input_tokens, output_tokens

    for i in range(5):
        if detected_leakage:
            answer, in_t, out_t = apply_steps(
                steps,
                charts,
                user_query,
                currency_market,
                currency_symbol,
                list_of_indicators,
                future_trading,
                symbols_of_indicators,
            )
            input_tokens += in_t
            output_tokens += out_t
            detected_leakage, in_t, out_t = leakage_detection(answer)
            input_tokens += in_t
            output_tokens += out_t
        else:
            break
    return answer, input_tokens, output_tokens


def apply_steps(
    steps,
    charts,
    user_query,
    currency_market,
    currency_symbol,
    list_of_the_indicators,
    future_trading,
    symbols_of_indicators,
):
    results = ""
    input_tokens = output_tokens = 0
    use_of_future_helper = False
    for i, step in enumerate(steps.values(), start=1):
        print(f"DEBUG Step {i}: {step}")
        tools_of_step = step.get("tools", [])
        tools_of_step_prompt = get_tools_of_step_prompt(tools_of_step, charts)
        is_final_step = i == len(steps)
        plan = step.get("plan")
        step_instruction, any_indicator_provided_prompt, future_trading_prompt = (
            get_step_instruction(
                charts,
                plan,
                tools_of_step,
                use_of_future_helper,
                user_query,
                i,
                is_final_step,
                list_of_the_indicators,
                future_trading,
                symbols_of_indicators,
            )
        )

        prompt = applying_plans_prompt.format(
            today_date=time.strftime("%Y-%m-%d"),
            plan_of_step=plan,
            tools_of_step_prompt=tools_of_step_prompt,
            results=results if i > 1 else "",
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            step=step_instruction,
            any_indicator_provided=any_indicator_provided_prompt,
            synced_signal=synced_signal_prompt if use_of_future_helper else "",
            long_short_signals_prompt=future_trading_prompt,
        )

        future_helper_prompt, spot_trading_no_leverage_message = (
            future_helper_agent(plan, currency_market)
            if not use_of_future_helper
            else ("", "")
        )
        if future_helper_prompt and not use_of_future_helper:
            plan += future_helper_prompt
            if spot_trading_no_leverage_message:
                plan += spot_trading_no_leverage_message
            try:

                answer, result_appender, in_t, out_t = step_invoke(
                    invoke_ReAct,
                    prompt=prompt,
                    step_number=i,
                    plan=plan,
                    ReAct_mode=True,
                )
                use_of_future_helper = True
                results += result_appender
                input_tokens += in_t
                output_tokens += out_t
            except Exception as e:
                answer, result_appender, in_t, out_t = step_invoke(
                    invoke, prompt=prompt, step_number=i
                )
                results += result_appender
                input_tokens += in_t
                output_tokens += out_t
        else:
            answer, result_appender, in_t, out_t = step_invoke(
                invoke, prompt=prompt, step_number=i
            )
            results += result_appender
            input_tokens += in_t
            output_tokens += out_t

    answer = remove_unwanted_text(answer)
    return answer, input_tokens, output_tokens


def handle_parsing_error(
    e,
    steps,
    charts,
    user_query,
    currency_market,
    currency_symbol,
    list_of_indicators,
):
    """
    Handle parsing errors by generating a comprehensive response that maintains quality
    and matches the user's query language.

    Args:
        e: The parsing error
        steps: The unparsed steps
        charts: Available chart data
        user_query: Original user query
        currency_market: Market type
        currency_symbol: Trading pair
        list_of_indicators: Available indicators

    Returns:
        tuple: (answer, input_tokens, output_tokens)
    """
    input_token = output_token = 0
    is_persian = any("\u0600" <= char <= "\u06ff" for char in user_query)
    future_trading_prompt, spot_trading_no_leverage_message = future_helper_agent(input_text=steps , currency_market=currency_market)

    plan_of_step = error_handeling_prompt.format(
        language="Persian" if is_persian else "English",
        charts=charts,
        currency_market=currency_market,
        currency_symbol=currency_symbol,
        list_of_indicators=list_of_indicators,
        steps=steps,
        user_query=user_query,
        tabular_format=tabular_format_prompt if future_trading_prompt else "",
    )
    
    if future_trading_prompt:
        prompt = applying_plans_prompt.format(
            today_date=time.strftime("%Y-%m-%d"),
            plan_of_step="",
            tools_of_step_prompt=f"These are the value of the tools you can use for applying steps:{charts}.\n",
            results=f"Analyze the data and steps using all tools and plans You are not generating the answer, you are just analyzing the data, Answer will be generated by an other agent;  This is User Query:`{user_query}`\n",
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            any_indicator_provided=list_of_indicators,
            step=steps,
            synced_signal="",
            long_short_signals_prompt=long_short_signals_prompt,
        )
        result_of_steps_except_future_trading, in_t, out_t = invoke(prompt=prompt)  
        input_token += in_t
        output_token += out_t
        prompt_of_react_agent = error_handeling_react_prompt.format(
            steps="",
            user_query=user_query,
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            result=result_of_steps_except_future_trading,
            future_trading_prompt=future_trading_prompt,
            spot_trading_no_leverage_message=spot_trading_no_leverage_message,
        )
        answer_of_react_agent , in_t, out_t = invoke_ReAct(system_prompt=prompt_of_react_agent, plan=future_trading_prompt)
        input_token += in_t
        output_token += out_t
        prompt = applying_plans_prompt.format(
            today_date=time.strftime("%Y-%m-%d"),
            plan_of_step=plan_of_step,
            tools_of_step_prompt="",
            results=f"Synthesize a comprehensive answer using the combined results of all previous analysis steps: {result_of_steps_except_future_trading + answer_of_react_agent}\n\nYour response must be in the same language as the user's original query: '{user_query}'\n\nIncorporate all relevant technical analysis, indicators, and trading signals into a single, well-structured response that directly addresses the user's request. Ensure all conclusions are supported by the data presented in previous steps.",
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            any_indicator_provided=list_of_indicators,
            step="",
            synced_signal="",
            long_short_signals_prompt=long_short_signals_prompt,
        )
    else:
        prompt = applying_plans_prompt.format(
        today_date=time.strftime("%Y-%m-%d"),
        plan_of_step=plan_of_step,
        tools_of_step_prompt=f"These are the value of the tools you can use for applying steps:{charts}.\n",
        results=f"Generate the whole answer in one step using all tools and plans; Your response should be in the same language as user query is in, This is user query:{user_query}\n",
        currency_market=currency_market,
        currency_symbol=currency_symbol,
        any_indicator_provided=list_of_indicators,
        step="",
        synced_signal="",
        long_short_signals_prompt = long_short_signals_prompt,
        )
            
    answer, in_t, out_t = invoke(prompt=prompt)
    input_token += in_t
    output_token += out_t
    answer = remove_unwanted_text(answer)

    return answer, input_token, output_token
