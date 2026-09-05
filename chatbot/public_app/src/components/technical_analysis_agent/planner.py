from public_app.src.prompts import technical_analysis_prompt, future_signal_prompt
from public_app.src.utilis import prompt_builder, chat_invoke
from .tools import preprocess_analysis_input, preprocess_planner_for_signal
import time


def technical_analysis_plan_creation(
    history,
    user_query,
    image_documents,
    currency_market,
    currency_symbol,
    name_of_the_indicators,
    charts,
):
    (
        extracted_queries,
        count_of_queries,
        future_trading,
        in_t_preprocess,
        out_t_preprocess,
        user_query,
    ) = preprocess_analysis_input(user_query)
    future_signal_text, long_short_signal_text, entry_point_text = (
        preprocess_planner_for_signal(
            future_trading,
            currency_market,
        )
    )
    step_numbers = (
        "6 to 8" if count_of_queries and (count_of_queries >= 3) else "4 to 6"
    )
    
    planner_prompt = prompt_builder(
        history=history,
        new_message=user_query,
        system_prompt=technical_analysis_prompt.format(
            today_date=time.strftime("%Y-%m-%d"),
            currency_market=currency_market,
            currency_symbol=currency_symbol,
            name_of_the_indicators=name_of_the_indicators,
            charts=charts,
            extracted_queries=extracted_queries,
            complex_step_numbers=step_numbers,
            future_signal_prompt=future_signal_text,
            long_short_signals=long_short_signal_text,
            entry_points_for_signals=entry_point_text,
        ),
        image_documents=image_documents,
    )
    plans, in_t, out_t = chat_invoke(planner_prompt)
    in_t += in_t_preprocess
    out_t += out_t_preprocess

    return plans, future_trading, in_t, out_t
