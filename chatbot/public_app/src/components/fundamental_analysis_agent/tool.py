from public_app.src.prompts import (
    miner_behavior_analysis_planner_prompt,
    network_valuation_analysis_planner_prompt,
    smart_money_flow_planner_prompt,
    whale_manipulation_detection_planner_prompt,
    miner_behavior_analysis_prompt,
    network_valuation_analysis_prompt,
    smart_money_flow_prompt,
    whale_manipulation_detection_prompt,
    miner_behavior_summary_prompt,
    network_valuation_summary_prompt,
    smart_money_flow_summary_prompt,
    whale_manipulation_summary_prompt,
    non_matching_strategy_prompt,
)
from public_app.src.utilis import make_human_readable
from public_app.src.utilis import (
    prompt_builder,
    chat_invoke,
    leakage_detection,
)

def retry_plan_fundamental_analysis(
    fundamental_analysis, strategy ,user_query, image_documents, history
):
    input_tokens = output_tokens = 0
    for i in range(5):
        plans, input_t, output_t = fundamental_plan_creation(
            fundamental_analysis, strategy, user_query, image_documents, history
        )
        input_tokens += input_t
        output_tokens += output_t
        leakage, in_t, out_t = leakage_detection(plans)
        input_tokens += in_t
        output_tokens += out_t
        if not leakage:
            return plans, input_tokens, output_tokens
    return plans, input_tokens, output_tokens


def fundamental_plan_creation(
    fundamental_analysis, strategy, user_query, image_documents, history
):
    planner_prompt  = preprocess_fundamental_analysis(fundamental_analysis , strategy)
    formatted_prompt = prompt_builder(history, user_query, planner_prompt, image_documents)
    plans, input_tokens, output_tokens = chat_invoke(formatted_prompt)
    return (
        plans,
        input_tokens,
        output_tokens,
    )


def fundamental_analysis_make_human_readable(properties):
    """
    Make the data human readable by converting timestamps to dates.
    Args:
        properties: Dictionary containing metric data with timestamps
    Returns:
        Dictionary with converted timestamps
    """
    if not properties:
        return properties

    for metric_name, metric_data in properties.items():
        if isinstance(metric_data, list):
            for data_point in metric_data:
                if isinstance(data_point, dict):
                    if "timestamp" in data_point:
                        timestamp = data_point["timestamp"]
                        if isinstance(timestamp, (int, float)):
                            if timestamp > 1e12:
                                timestamp = timestamp / 1000
                            from datetime import datetime

                            date = datetime.fromtimestamp(timestamp)
                            data_point["timestamp"] = date.strftime("%Y-%m-%d %H:%M:%S")

    return properties


def preprocess_data(fundamental_analysis):
    """
    Preprocess the data to be used by the fundamental analysis agent.
    Args:
        data: Dictionary containing analysis data
    Returns:
        Processed properties with human readable dates
    """
    startDate = make_human_readable(
        fundamental_analysis.get("startDate", ""), mode=False
    )
    endDate = make_human_readable(fundamental_analysis.get("endDate", ""), mode=False)
    market = fundamental_analysis.get("market", "")
    asset = fundamental_analysis.get("asset", {})
    chain = fundamental_analysis.get("chain", {})
    data = fundamental_analysis.get("data", {})
    if data:
        for k ,v in data.items():
            if len(v) >= 50:
                data[k] = data[k][-50:] 
        data = fundamental_analysis_make_human_readable(data)
    return data, startDate, endDate, market, asset, chain


def applying_strategy_prompt_chooser(strategy):
    if strategy == "minerbehavioranalysis":
        return miner_behavior_analysis_prompt
    elif strategy == "networkvaluationanalysis":
        return network_valuation_analysis_prompt
    elif strategy == "smartmoneyflow":
        return smart_money_flow_prompt
    elif strategy == "whalemanipulationdetection":
        return whale_manipulation_detection_prompt
    else:
        return "You are a fundamental analysis agent. You are given a dataset and you need to analyze it. You need to return the analysis in the same language as the user query. Your response should be in the same language as the user query if user query is in persian you can not answer in english."


def summary_prompt_chooser(strategy):
    if strategy == "minerbehavioranalysis":
        return miner_behavior_summary_prompt
    elif strategy == "networkvaluationanalysis":
        return network_valuation_summary_prompt
    elif strategy == "amartmoneyflow":
        return smart_money_flow_summary_prompt
    elif strategy == "whalemanipulationdetection":
        return whale_manipulation_summary_prompt
    else:
        return False


def planner_prompt_chooser(strategy):
    if strategy == "minerbehavioranalysis":
        return miner_behavior_analysis_planner_prompt
    elif strategy == "networkvaluationanalysis":
        return network_valuation_analysis_planner_prompt
    elif strategy == "smartmoneyflow":
        return smart_money_flow_planner_prompt
    elif strategy == "whalemanipulationdetection":
        return whale_manipulation_detection_planner_prompt
    else:
        return non_matching_strategy_prompt

def preprocess_fundamental_analysis(fundamental_analysis, strategy ):
    """
    Preprocess the data to be used by the fundamental analysis agent.
    Args:
        data: Dictionary containing analysis data
    Returns:
        Formatted prompt with processed properties
    """
    planner_prompt = planner_prompt_chooser(strategy)

    data, startDate, endDate, market, asset, chain = preprocess_data(
        fundamental_analysis
    )
    number_of_steps = len(data)
    parameters = list(data.keys())
    
    formatted_planner_prompt = planner_prompt.format(
        startDate=startDate,
        endDate=endDate,
        market=market,
        asset_symbol=asset["symbol"],
        asset_name=asset["name"],
        chain_name=chain["name"],
        number_of_steps=number_of_steps,
        parameters=parameters,
    )

    return formatted_planner_prompt
