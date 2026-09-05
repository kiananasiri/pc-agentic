from public_app.src.utilis import (
    invoke,
    parse_json_answer,
    parse_list_answer,
    make_human_readable,
    switch_case_resolution,
    make_human_readable_indicators,
    invoke_ReAct,
)
from ast import literal_eval
from public_app.src.prompts import (
    preprocess_analysis_input_prompt,
    future_signal_prompt,
    long_short_signals_prompt,
    future_trading_prompt,
    last_step_instruction_prompt,
    tabular_format_prompt,
    use_all_indicators_prompt,
    leverage_calculation_prompt,
)
import re


def check_if_future_trading(user_input):
    future_keywords = {
        "فیوچر",
        "فیوچرز",
        "سیگنال",
        "استاپ‌لاس",
        "استاپ لاس",
        "future",
        "futures",
        "future trading",
        "futures trading",
    }
    return any(keyword in user_input.lower() for keyword in future_keywords)


def preprocess_analysis_input(user_input):
    future_trading = True if check_if_future_trading(user_input) else False
    
    if future_trading:
        user_input += leverage_calculation_prompt
    
    prompt = preprocess_analysis_input_prompt.format(user_input=user_input)
    queries, in_t, out_t = invoke(prompt=prompt)
    try:
        output = parse_json_answer(queries)
        queries = output.get("queries")
        list_of_queries = parse_list_answer(queries)
        for i, query in enumerate(list_of_queries, start=1):
            list_of_queries[i - 1] = f"User Query{i}: " + query

        return (
            f"These are queries (1 to {len(list_of_queries)}), You should consider :\n"
            + "\n".join(list_of_queries),
            len(list_of_queries),
            future_trading,
            in_t,
            out_t,
            user_input,
        )

    except Exception as e:
        return queries, None, future_trading, in_t, out_t, user_input


def get_tool_values(tools_of_step, charts):
    tools_values = {}
    options = {}
    inputs = {}
    if charts:
        if not isinstance(tools_of_step, list):
            tools_of_step = literal_eval(tools_of_step)

        for tool in tools_of_step:
            tool = tool.lower().strip()
            l_tool = tool.split("_")
            serach = re.search(r"\d+", l_tool[0])
            chart_number = tools_of_step[0][serach.span()[0] : serach.span()[1]]
            chart = charts[int(chart_number) - 1]
            if "_".join(l_tool[1:]) == "price_history":
                tools_values["price_history"] = make_human_readable(chart.get("ohlcv"))
            else:
                try:
                    full_name, value, option, input = get_indicator(
                        chart.get("indicators"), tool
                    )
                    tools_values[f"{tool} ({full_name})"] = value
                    options[f"option of {tool} ({full_name})"] = option
                    if input:
                        inputs[f"the {tool} is calculated on "] = (
                            f"{', '.join(input)} of price history"
                        )
                except Exception as e:
                    continue
        return tools_values, options, inputs
    else:
        return {}, {}, {}


def get_tools_of_step_prompt(tools_of_step, charts):
    if tools_of_step:
        tools_values, options, inputs = get_tool_values(tools_of_step, charts)
        if tools_values:
            tools_of_step_prompt = f"""Tools for this Instruction you have:{{{tools_values}}}\n{options if options else ""}\n{inputs if inputs else ""}"""
        else:
            tools_of_step_prompt = ""
    else:
        tools_of_step_prompt = ""

    return tools_of_step_prompt


def get_indicator(indicators, tool):
    for ind in indicators:
        if ind.get("symbol") == tool:
            full_name = ind.get("fullName")
            output_tuples = list(ind.get("outputs").items())
            outputs = {}
            for value in output_tuples:
                outputs[value[0]] = make_human_readable_indicators(value[1])
            return full_name, outputs, ind.get("options", None), ind.get("inputs", None)
    return None, {}, None, None


def get_name_option_period(indicators):
    indicators_prompt = ""
    for ind in indicators:
        try:
            symbol, name, option, input = (
                ind.get("symbol"),
                ind.get("fullName", ""),
                ind.get("options", ""),
                ind.get("inputs", ""),
            )
            indicators_prompt += (
                f"""\n{symbol}: {name} Inputs:{input} Options:{option}"""
            )
        except Exception as e:
            continue
    return indicators_prompt


def get_list_of_indicators(indicators: list, chart_number: int, resolution=""):
    name = []
    for indicator in indicators:
        name.append(
            f"chart{chart_number}_{indicator.get('symbol')}_{resolution}_resolution"
        )
    return name


def preprocess_indicators(indicators, formatted_indicators):
    for i, ind in enumerate(indicators):
        ind["symbol"] = formatted_indicators[i]
    return indicators


def get_charts(charts):
    prompt = ""
    list_of_indicators = []
    symbols_of_indicators = []

    if charts:
        len_charts = len(charts)
        prompt = f"You are provided with {len_charts} charts:\n"
        for i, chart in enumerate(charts, start=1):
            try:
                price_history = chart.get("ohlcv", None)
                if price_history:
                    list_of_indicators.append(f"chart{i}_price_history")

                indicators = chart.get("indicators", None)
            except Exception as e:
                continue

            resolution_base_unit = (
                switch_case_resolution(resolution=chart.get("resolution"))
                if chart.get("resolution")
                else ""
            )
            if indicators:
                for indicator in indicators:
                    if indicator.get("symbol"):
                        symbols_of_indicators.append(indicator.get("symbol"))

                list_of_indicators_of_chart = get_list_of_indicators(
                    indicators, i, resolution_base_unit
                )
                chart["indicators"] = indicators = preprocess_indicators(
                    indicators, list_of_indicators_of_chart
                )
                list_of_indicators.extend(list_of_indicators_of_chart)

            prompt += (
                f"""\n**Chart {i} Informataion:** spans date from {chart.get("startDate")} till {chart.get("endDate")} with a resolution of {resolution_base_unit}.\n"""
                + (
                    (
                        f"indicators of chart{i} and informatio of each indicator:"
                        + f"{get_name_option_period(indicators)}"
                    )
                    if indicators
                    else f"You have no indicator for chat{i}, So you can not use any price history of currency from your knowledge(your knowledge of price is outdated e.g. BTC is not 20k$ any more."
                )
            )
            if not indicators and price_history:
                prompt += f"\n**The only tool of chart{i} is chart{i}_price_history not ny other tools. This is critacal, if you put any other tool in tools field of each step, it will lead to key error in dictionary. SO PAY VERY CLOSE ATTENTION TO ONLY YOU CAN 'chart{i}_price_history' AS TOOL in your steps.** Since it has already been collected, no additional steps, such as 'Collect the price history,' are necessary."
            elif indicators and price_history:
                prompt += f"\nchart{i}_price_histoty,  Since it has already been collected, no additional steps, such as 'Collect the price history,' are necessary."

        if not list_of_indicators:
            prompt += "**Thre is no indicator and no price history provided: 1.you can not use any indicator and any price hictory by your knowledge 2.you can not calculate any indicator by your knowledge. This means none of your steps should have price history as tool or any tool.**"

    return prompt, list_of_indicators, symbols_of_indicators


def prepare_analysis_data(analysis):
    charts = analysis.get("charts", None)
    charts_prompt, list_of_indicators, symbols_of_indicators = get_charts(charts)
    list_of_indicators_prompt = (
        f"You must use all tools provided from {1} to {len(list_of_indicators)}: "
        + " ".join(
            [
                f"{i}. {indicator}"
                for i, indicator in enumerate(list_of_indicators, start=1)
            ]
        )
        if list_of_indicators
        else "There is no indicator or price history provided to you, your tools field for all steps must be an empty list Also consider in your plans **You can not have any stpes like `Analyze the price history` or `Identify the overall market trend for any currecny based on available indicators and price history` because no price history is given and you can not use your knowledeg for extarcting price history (they are not valid any more).**"
    )
    currency_market = analysis.get("market", None)
    currency_symbol = analysis.get("pair", None)
    return (
        charts,
        charts_prompt,
        list_of_indicators,
        list_of_indicators_prompt,
        currency_market,
        currency_symbol,
        symbols_of_indicators,
    )


def prepare_indicators_info(indicators):
    if indicators:
        indicators_exit_in_tools = []
        name_of_the_indicators = list(indicators.keys())

        for i, indicator_name in enumerate(name_of_the_indicators, start=2):
            full_name = indicators[indicator_name].get("name", indicator_name)
            indicators_exit_in_tools.append(f"Indicator {i}: {full_name}")
            options = indicators[indicator_name].get("options")
            if options:
                indicators_exit_in_tools.append(
                    f"Options of Indicator {full_name}: {options}"
                )

        return indicators_exit_in_tools, name_of_the_indicators
    return indicators, []


def get_step_instruction(
    charts,
    step_plan,
    tools_of_step,
    use_of_future_helper,
    user_query,
    step_number,
    is_final_step,
    list_of_indicators,
    future_trading,
    symbols_of_indicators,
):
    try:
        if tools_of_step:
            chart_number = tools_of_step[0].split("_")[0][-1]
            resolution = (
                charts[int(chart_number) - 1].get("resolution", "")
                if tools_of_step
                else ""
            )
        else:
            resolution = ""
    except Exception as e:
        resolution = ""

    future_trading_prompt = (
        long_short_signals_prompt
        if future_trading
        else "You are not allowed to provide any long or short signals. DO NOT PROVIDE ANY ENTRY POINTS, STOP LOSS, TAKE PROFIT, OR LEVERAGE RATIO."
    )
    if not list_of_indicators:
        any_indicator_provided_prompt = "always consider, you have no indicators and no price history provided, you can not use any indicator and any price history from your knowledge(e.g. BTC is not 20k$ anymore)"
    else:
        any_indicator_provided_prompt = ""
    
    parameter_plan, _ =future_helper_agent(input_text=step_plan, currency_market="crypto:futures" if future_trading else "crypto:spot")
    
    non_final_step_instruction = f"""this is the only do what the step  number {step_number} so only instruction says and do not generate the final answer, the final answer will be generated at the last step {("You are an indicator specialist in currency. First, consider how each indicators is used. Then, apply them according to the given instruction") if len(list_of_indicators) > 2 else ""}"""

    if not is_final_step and parameter_plan and not use_of_future_helper and future_trading:
        if resolution:
            timeframe_warning = f"\n\n**⚠️ توجه به تایم‌فریم {resolution}:**\n"
            if resolution == "1h":
                timeframe_warning += "- Minimum SL for 1 hour: 1.5%\n"
                timeframe_warning += "- Maximum SL for 1 hour: 8%\n"
                timeframe_warning += (
                    "- **Never use 1% SL** - too tight\n"
                )
            elif resolution in ["1m", "5m"]:
                timeframe_warning += f"- Minimum SL for {resolution}: 0.5%\n"
                timeframe_warning += f"- Maximum SL for {resolution}: 3%\n"
            elif resolution == "15m":
                timeframe_warning += "- Minimum SL for 15 minutes: 2.0%\n"
                timeframe_warning += "- Maximum SL for 15 minutes: 8%\n"
            elif resolution == "4h":
                timeframe_warning += "- Minimum SL for 4 hours: 2.5%\n"
                timeframe_warning += "- Maximum SL for 4 hours: 12%\n"
            elif resolution in ["1d", "daily"]:
                timeframe_warning += "- Minimum SL for daily: 4%\n"
                timeframe_warning += "- Maximum SL for daily: 20%\n"
            # Add clarification about percentage reference and final SL value
            timeframe_warning += "- تمام درصدهای ذکر شده نسبت به قیمت ورود (Entry Price) هستند، اما مقدار نهایی SL باید همیشه به صورت قیمت دقیق (Price) ارائه شود، نه درصد یا تعداد کوین.\n"
            non_final_step_instruction += timeframe_warning
            

    if is_final_step:

        if future_trading:
            signal_conflicts_prompt = """
        ### سیگنال قوی‌ترین و قابل‌اعتمادترین را بر اساس:
            - هم‌راستایی اکثر اندیکاتورها
            - قوت شواهد پشتیبانی
            - قابلیت‌اعتماد سیگنال‌ها
        * تنها یک سیگنال واضح (یا بلند یا کوتاه) که شواهد قوی‌تری دارد، ارائه دهید
        * در استدلال خود از اندیکاتورها استفاده کنید، اما سیگنال‌ها باید بر اساس **ارزش‌های قیمت ارز ارائه‌شده** (شما نمی‌توانید از ارزش‌هایی که از دانش خود دارید استفاده کنید، مثلاً BTC دیگر 20 هزار دلار نیست)
        * **مهم: شما باید مقادیر دقیق قیمت ارائه دهید، نه محدوده‌ها**
        *  اگر سیگنال‌های متضادی وجود دارد، آن را که شواهد قوی‌تری دارد، انتخاب کنید و توضیح دهید که چرا آن را بر دیگران ترجیح می‌دهد"""
        else:
            signal_conflicts_prompt = ""


        is_persian = any(
            char in user_query for char in "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
        )
        response_language = "Persian فارسی (fa)" if is_persian else "English"
   

        last_step_instruction_formatted = last_step_instruction_prompt.format(
            signal_conflicts_prompt=signal_conflicts_prompt,
            response_language=response_language,
            use_list_of_indicators_prompt=(
                use_all_indicators_prompt.format(
                    numbered_indicators=".\n".join(
                        [
                            f"{i}. {indicator}: "
                            for i, indicator in enumerate(
                                symbols_of_indicators, start=1
                            )
                        ]
                    )
                )
                if list_of_indicators
                else ""
            ),
            tabular_format=tabular_format_prompt if future_trading else "",
        )

        return (
            last_step_instruction_formatted,
            any_indicator_provided_prompt,
            future_trading_prompt,
        )

    return (
        non_final_step_instruction,
        any_indicator_provided_prompt,
        future_trading_prompt,
    )


def preprocess_planner_for_signal(future_trading, currency_market):
    future_signal_text = ""
    long_short_signal_text = ""
    entry_point_text = ""

    if future_trading:
        leverage_note = (
            "* currency market is crypto:spot Leverage Ratio (LR) is not applicable for spot trading at all."
            if currency_market == "crypto:spot"
            else ""
        )
        future_signal_text = future_signal_prompt.format(
            currency_market_no_leverage=leverage_note
        )
        entry_point_text = "- **CRITICAL: You must provide EXACT PRICE VALUES, not ranges. Your entry points values and parameters must be based on prices in price history. Make sure before the step for providing signals and entry points you analyze price history to extract exact price values. ALWAYS provide specific price levels for EP, SL, and TP - never use ranges or approximate values. NEVER use your trained knowledge for current prices - ONLY use the provided price history data.**"
        long_short_signal_text = "###" + long_short_signals_prompt
    else:
        future_signal_text = ""
        long_short_signal_text = "You are not allowed to provide any long or short signals.DO NOT GIVE ANY ENTRY POINTS."
        entry_point_text = "- **DO NOT GIVE ANY ENTRY POINTS, STOP LOSS, TAKE PROFIT, OR LEVERAGE RATIO.**"
    return future_signal_text, long_short_signal_text, entry_point_text


def future_helper_agent(input_text, currency_market):
    spot_trading_no_leverage_message = ""
    if currency_market == "crypto:spot":
        spot_trading_no_leverage_message = "Leverage Ratio (LR) is not applicable for spot trading. Do not calculate leverage. "

    trading_params = [
       "RR",
       "LR",
        "risk to reward",
        "risk to reward ratio",
        "risk-to-reward ratio",
        "risk-to-reward",
        "leverage ratio",
        "leverage", 
        "(RR)",
        "(LR)",
        
    ]
    if any(param in input_text.lower() for param in trading_params):
        return future_trading_prompt, spot_trading_no_leverage_message

    return "", ""


def step_invoke(invoke, prompt, step_number, plan="", ReAct_mode=False):
    if ReAct_mode:
        plan_formatted = (
            """You must define Risk to Reward and Leverage Ratio. Write down step by step how you calculated the risk to reward and leverage ratio."""
            + plan
        )
        answer, in_t, out_t = invoke_ReAct(system_prompt=prompt, plan=plan_formatted)
        result_appender = f"""\n**step{step_number} results**: {answer}"""
        return answer, result_appender, in_t, out_t

    answer, in_t, out_t = invoke(prompt=prompt)

    result_appender = f"""\n**step{step_number} results**: {answer}"""
    return answer, result_appender, in_t, out_t
